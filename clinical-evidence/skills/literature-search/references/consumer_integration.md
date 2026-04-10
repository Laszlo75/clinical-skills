# Consumer integration guide

**Audience:** Any skill that consumes a literature-search YAML reference ledger — today that is `protocol-reviewer`; tomorrow it will also be `literature-review`; later it may be other skills entirely.

**Purpose:** A single place that documents how a downstream skill plugs into the literature-search pipeline. If you are building a new consumer, read this file; you should not need to re-invent discovery, validation, or auto-triggering logic.

---

## The pipeline in one picture

```
┌──────────────────┐                        ┌─────────────────────────────┐
│ literature-search│ ─ writes ledger ─▶    │ workspace folder            │
│ (producer)       │   to hidden path       │  ├─ Topic_Evidence_....docx │ ← user-facing
└──────────────────┘                        │  ├─ Topic_Evidence_....md   │ ← user-facing
                                            │  ├─ Topic_References.bib    │ ← user-facing
                                            │  ├─ Topic_PMIDs.txt         │ ← user-facing
                                            │  └─ .literature_search_     │
                                            │       ledger.yaml           │ ← hidden / internal
                                            └──────────────┬──────────────┘
                                                           │
                                   ┌───────────────────────┼───────────────────────┐
                                   ▼                       ▼                       ▼
                         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
                         │ protocol-reviewer│   │ literature-review│   │  future consumer │
                         │  (consumer)      │   │  (consumer)      │   │  (consumer)      │
                         └──────────────────┘   └──────────────────┘   └──────────────────┘
```

All consumers share the same three-step onboarding: **discover** the ledger, **validate** it, **consume** it. The researcher is never asked about the ledger — it is a hidden file that exists purely to enable the handoff and to anchor the producer's anti-hallucination writes.

---

## Prerequisite: read the schema

Before you write any consumer code or prompt instructions, read [`ledger_schema.md`](./ledger_schema.md). It is the authoritative contract — field names, types, required vs optional, the grade object, everything. Do not memorise the schema from this file or from the producing skill's SKILL.md. The schema file is the source of truth.

One fact worth internalising from the schema before you read on: **the ledger always lives at exactly one path** — `<workspace>/.literature_search_ledger.yaml`. That path is fixed. There is no filename the consumer has to guess, no pointer file to parse, no "which ledger did you mean?" ambiguity. The whole discovery flow below is built on that single invariant.

---

## Step 1 — Discovery: find the ledger

There is exactly one place to look:

```
<workspace>/.literature_search_ledger.yaml
```

The workspace is the directory the researcher is working in — the same directory the consumer is about to write its own output into. Resolve the path, check whether the file exists, and branch on that.

### Case A — the ledger file exists

Proceed to Step 2 (Validation). Do not ask the researcher anything. The whole point of the fixed hidden path is that a researcher who has just run a literature search in this folder, and now asks for a protocol review (or a narrative review, or any other downstream action), can say "review this protocol" and the consumer silently picks up the evidence without a word about files or formats.

A single, lightweight confirmation is still good manners once the ledger has loaded — something like: "Using the evidence I pulled together on *[topic]* on *[search_date]* — let me know if you'd rather I re-run the search." One line, no path, no filename. Optional skip if the consumer already has high confidence the topic is aligned.

### Case B — the ledger file does not exist

Auto-trigger a fresh literature search. The literature-search skill lives as a sibling directory: read `../literature-search/SKILL.md` and follow its complete workflow. When that workflow finishes, literature-search will have written the ledger to exactly the canonical path, so the consumer can loop back and proceed as in Case A.

If `../literature-search/SKILL.md` is not found at that relative path, stop and tell the researcher in plain language:

> "I don't have any evidence to work from yet, and I can't find the literature-search skill to run one. Please install literature-search alongside this skill, or run a literature search first."

Do not ask the researcher to provide a YAML file. The ledger is an internal artifact — researchers should never see it, edit it, or be asked about it.

### Why not support "user provides a ledger file directly"?

An earlier draft of this guide offered three discovery paths, including one where the researcher could hand-attach a ledger. That path has been removed deliberately:

1. **It leaks the abstraction.** The moment a researcher is asked "do you have a YAML ledger?" they stop trusting the skill to manage evidence for them.
2. **It creates two code paths to keep in sync.** Every consumer would have to handle both "parsed pointer" and "attached file" discovery, with their own edge cases.
3. **It's unnecessary.** If the researcher has a ledger in a different workspace, the right move is to run the consumer in the workspace that already contains the ledger — not to attach files across folders.

Keep it single-path. One canonical location. Exists or doesn't exist.

---

## Step 2 — Validation: run the validator

Never trust a ledger without running the validator first. The validator is a Python script bundled with literature-search:

```bash
python ../literature-search/scripts/validate_ledger.py <workspace>/.literature_search_ledger.yaml
```

Exit codes:
- `0` — valid. Warnings (if any) are informational; you may surface them to the researcher but you can proceed.
- `1` — one or more ERROR lines in output. **Do not proceed.** Show the errors to the researcher in plain language and offer to re-run the literature search.
- `2` — file missing or unparseable YAML. Treat this the same as "file missing" from Step 1 — auto-trigger literature-search.

**Why a script and not prose:** executable checks cannot drift from the schema. A prose checklist in your SKILL.md will eventually fall out of sync with what literature-search produces. The script is bundled with the producer, so it always matches.

**What the script checks** (so you know what's been verified without having to re-read it):
- Top-level sections: `metadata`, `guidelines`, `references` present.
- `metadata.ledger_schema_version` is present and is a `1.x` version this consumer supports.
- `metadata.topic`, `search_date`, `skill_version`, `model_id` present.
- `search_date` parseable as ISO 8601 YYYY-MM-DD.
- Every reference has `pmid`, `doi`, `title`, `first_author`, `source`.
- Every `doi` matches `^10\.\d{4,9}/`.
- Every non-null `pmid` is numeric.
- Every `source` is one of `pubmed`, `scholar_gateway`, `both`.
- `ref_id` values are unique across `guidelines` and `references`.
- No duplicate DOIs.
- No `[Retracted]` / `[Retraction of:` markers in titles.
- Every `key_recommendations[].grade` is a structured object with `system`, `code`, `display`.

Your consumer does not need to re-check any of this. Trust the exit code.

---

## Step 3 — Consume: load the ledger into working memory

Read the YAML into your skill's context. The fields you will most commonly use:

- **`metadata.topic`** — the search topic, to confirm scope alignment with the researcher's current task.
- **`metadata.search_date`** — to gauge freshness and to cite in the transparency disclaimer.
- **`metadata.ledger_schema_version`** — record it in your output so the audit trail is complete.
- **`metadata.skill_version`** and **`metadata.model_id`** — for the transparency disclaimer of your output document.
- **`guidelines[].key_recommendations[].grade.display`** — the human-readable grade for inline citation in your document.
- **`guidelines[].key_recommendations[].grade.system` + `.code`** — for programmatic filtering or aggregation.
- **`references[].pmid`, `.doi`, `.title`, `.first_author`, `.authors_full`, `.journal`, `.year`, `.volume`, `.pages`** — for building reference lists and BibTeX entries. **Copy these verbatim** — do not reformat, reorder, or reconstruct.
- **`references[].key_finding`** — the producer's one-sentence summary; useful for mapping references to your output sections.
- **`preprints[]`** and **`ongoing_trials[]`** — optional sections; check whether they exist before iterating.

### Reference integrity — your responsibility

The producer has already verified DOIs, PMIDs, titles, and authors character-by-character against PubMed. You do not need to re-verify. **But you must not corrupt what you copy.** Copy fields directly from the parsed YAML into your output — never reconstruct a DOI from the title or a title from the authors.

### Staleness — your responsibility

`metadata.search_date` tells you how old the evidence is. It is the consumer's job, not the producer's, to decide whether that is fresh enough for the task at hand. A review of a rapidly moving field against a six-month-old ledger may warrant offering the researcher a fresh search; a stable guideline topic against a three-month-old ledger is probably fine to use as-is. Surface the date to the researcher in the one-line confirmation from Step 1, and let them make the call.

---

## Schema version handling

Your consumer must declare which schema MAJOR version it targets — e.g., "this consumer supports ledger_schema_version 1.x". Write that into the consumer's SKILL.md.

When you parse `metadata.ledger_schema_version`:

- **Missing field** — error. This is a legacy unversioned ledger; the researcher must re-run the search. The validator will flag this with a clear error.
- **Matches your MAJOR** (e.g., consumer targets 1.x and ledger is 1.0, 1.1, 1.2) — accept silently.
- **Higher MAJOR** (e.g., consumer targets 1.x and ledger is 2.0) — warn clearly: "The evidence in this workspace was produced by a newer version of the search skill than this consumer understands. Some fields may have moved or been renamed. I'd recommend updating this consumer before proceeding." Stop unless the researcher overrides.
- **Lower MAJOR** (e.g., consumer targets 2.x and ledger is 1.0) — warn and stop. The consumer assumes fields that may not exist.

The validator handles most of this check for you — trust its exit code.

---

## Directory convention

Consumers and the producer are installed as **sibling directories** under the researcher's skills folder:

```
skills/
├── literature-search/        ← producer
│   ├── SKILL.md
│   ├── references/
│   │   ├── ledger_schema.md
│   │   └── consumer_integration.md  ← this file
│   └── scripts/
│       └── validate_ledger.py
├── protocol-reviewer/        ← consumer
│   └── SKILL.md
└── literature-review/        ← future consumer
    └── SKILL.md
```

This convention is what allows `../literature-search/...` to work from any consumer. If a user installs the skills somewhere else, they must preserve the sibling structure or the auto-trigger path in Step 1 Case B breaks. Document this in your consumer's SKILL.md so the user knows.

---

## What a consumer's SKILL.md should contain (minimal template)

```markdown
## Prerequisites

This skill consumes a hidden YAML reference ledger produced by the literature-search skill.
Read `../literature-search/references/ledger_schema.md` for the schema and
`../literature-search/references/consumer_integration.md` for the integration pattern.
The researcher should never be asked about the ledger directly.

## Loading the evidence

1. Discover: look for `.literature_search_ledger.yaml` in the workspace folder.
   - If it exists, proceed to validation.
   - If it does not exist, auto-trigger literature-search via `../literature-search/SKILL.md`;
     when it finishes, the ledger will be at the canonical path.

2. Validate: run `python ../literature-search/scripts/validate_ledger.py <workspace>/.literature_search_ledger.yaml`.
   - Exit 0 → proceed.
   - Exit 1 → show the researcher the errors in plain language and offer to re-run the search.
   - Exit 2 → treat as "missing" and auto-trigger the search.

3. Consume: read fields from the YAML as documented in `ledger_schema.md`.
   Copy reference metadata verbatim. Use `grade.display` for inline citations.
   Never mention the YAML file or its path to the researcher in the final output.
```

That is the entire contract. Everything else is your consumer's own logic.

---

## Example — how literature-review will plug in

Imagine a future `literature-review` skill that takes the same evidence and produces a narrative prose review:

1. Researcher says "write me a literature review on CMV prophylaxis in SOT".
2. Skill looks for `.literature_search_ledger.yaml` in the workspace.
3. If present, it validates silently, confirms the topic with the researcher in one line ("Using the CMV-in-SOT evidence from 2026-04-10 — say so if you'd rather I re-run the search"), and proceeds. If absent, it auto-triggers literature-search; when that finishes it loops back to step 2.
4. It loads `guidelines[]` to frame the current standard of care.
5. It loads `references[]` and uses `key_finding` to structure the narrative sections.
6. It groups recommendations by `grade.system` and `grade.code` to highlight consensus.
7. It includes preprints (if any) in a "Recent developments" section, clearly labelled as non-peer-reviewed.
8. It generates a `.md` + `.docx` output with the same transparency disclaimer pattern.

At no point does the researcher see, touch, or hear about a YAML file. No new schema. No new validation logic. No new discovery code. The same three steps.

This is why the contract lives in one place.
