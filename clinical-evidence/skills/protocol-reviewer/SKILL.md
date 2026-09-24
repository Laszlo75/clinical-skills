---
name: protocol-reviewer
model: opus
effort: high
description: >
  Review and update clinical protocols against current evidence and national guidelines.
  Automatically picks up recent evidence from the workspace or triggers a fresh literature
  search when needed. Use when a user uploads a clinical protocol, guideline, or standard
  operating procedure (SOP) and wants it reviewed, updated, or benchmarked against current
  best practice. The researcher never has to manage reference files — this skill handles
  the evidence handoff invisibly. Triggers include: "review this protocol", "update this
  guideline", "check this against latest evidence", "is this protocol still current",
  "compare to BTS/NICE/SIGN guidelines", or any request involving a clinical document
  that needs modernising. Also triggers when the user uploads a medical PDF and asks for
  recommendations, changes, or an evidence check.
---

# Clinical Protocol Reviewer

Take an existing clinical protocol, test each thing it tells clinicians to do against
current UK and international guidelines and the best recent evidence, and produce a draft
review a consultant-led MDT can act on — with every recommendation traceable from the
protocol statement, through the question asked and the evidence found, to the verdict.

The reader is a consultant-level clinician. Write at peer level: precise, direct, no
over-hedging. Where evidence is weak or conflicting, say so plainly; where the protocol is
already right, say that too.

Run on the latest Claude Opus at high effort (see the plugin README for the current
model; in Claude Cowork, choose it in the app). The lead works economically: bulky
reading (abstracts, full texts, guideline pages) happens inside the search agents, which
run in parallel; this conversation sees only their short summaries.

## Paths

Paths in this skill are relative to its base directory (the folder holding this
SKILL.md). Commands run from the researcher's workspace, so write `[skill-path]` as that
absolute base directory, quoted, and `<workspace>` as the researcher's folder. Shared
scripts are in `[skill-path]/../../shared/scripts/`; working files go in
`<workspace>/.clinical-evidence/` (hidden — never mention them to the researcher).

## Workflow

1. **Map the protocol.** Read it in full and write `protocol_map.yaml`: the protocol's
   title, version, date, institution, domain and population; every concrete statement a
   clinician would act on — drug, dose, threshold, timing, procedure, monitoring — with
   its section; and the review questions those statements raise (usually 4–10, PICO-style,
   each linked to its statements). Format: see the docstring of `review_tables.py`.

2. **Confirm scope — the one checkpoint.** Show the researcher, briefly: your reading of
   the protocol (population, setting, date), and the numbered review questions. Ask them
   to confirm or adjust (e.g. adult only? UK guidance only?). Don't search until they
   have answered — this is what makes the review answer their question.

3. **Get a verified evidence base.** Follow
   [`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md).
   In one message, dispatch 2–3 `guideline-search` agents, split by guideline body, each
   with all the questions and the protocol's concrete doses, thresholds and timings
   (guidelines are the backbone of the review: they read the current guideline documents
   and copy each grade as printed), and one `evidence-search` agent per cluster of 2–4
   question clusters for the literature. Merge, then check the references' identifiers (a quick PubMed ID
   conversion — no extra agent).

4. **Judge each statement.** Write `judgements.yaml`: for each statement (and any
   important omission, as `new_addition`), a verdict —

   | Verdict | Meaning |
   |---|---|
   | aligned | Matches current guidelines and evidence |
   | minor_update | Approach sound; wording, dose or detail needs adjusting |
   | major_update | Guidelines or evidence now support materially different practice |
   | new_addition | Not covered, but should be |
   | remove | Outdated or no longer recommended |

   — plus an actionable recommendation, the ledger `ref_id`s it rests on, the guideline
   grade (`grade.display` verbatim, only from a cited guideline whose grade the validator
   confirmed in its source text; leave it empty when no guideline grades the point), confidence (high/moderate/low), and flags for patient
   safety and commissioning impact. Weigh conflicting sources explicitly. Where no
   guideline covers a point, still recommend on consistent trends, observational data or
   expert opinion — ungraded, with the evidence cited, its certainty stated plainly and
   confidence set to match.

5. **Second review — where it changes practice.** Dispatch the `second-reviewer`
   agent with the paths to the map, the judgements and the ledger, the list of judgement
   ids to review — every `major_update`, `new_addition` and `remove`, plus anything
   flagged for safety — and `.clinical-evidence/second_review.yaml` as its output.
   Aligned and minor items are not sent; skip the step entirely if there are none. With
   more than about eight items, split them between two reviewers dispatched in the same
   message (`second_review_1.yaml`, `second_review_2.yaml`), keeping related items
   together.
   Reconcile every `disagree` or `unsupported` into **one** recommendation, recording
   status, note, `outcome` and a written `resolution` in the judgement's `second_review`:
   - `revised` — the challenge holds; change the judgement.
   - `kept` — the evidence supports your original judgement; say why.
   - `mdt_decision` — both positions are defensible and the evidence doesn't settle it.
     List the `options` (at least two), each with its position, cited pros and cons,
     and evidence; the document presents them for the MDT to decide rather than picking one.
   Don't settle a disagreement by retreating to "per unit protocol" when a guideline
   gives a specific value. Add judgements for any `missing` issues you agree with. The
   second reviewer's view stays in the traceability files; the document shows only the
   reconciled result.

6. **Build the tables and register row:**

   ```bash
   python "[skill-path]/../../shared/scripts/review_tables.py" \
     --ledger "<workspace>/.literature_search_ledger.yaml" \
     --map "<workspace>/.clinical-evidence/protocol_map.yaml" \
     --judgements "<workspace>/.clinical-evidence/judgements.yaml" \
     --prefix "[Protocol_Name]" --outdir "<workspace>" \
     --register "<workspace>/clinical-evidence-register.csv" \
     --model-id "<model id (configured: opus, effort high)>" --skill-version "<plugin version>"
   ```

   It refuses to build if anything is inconsistent — an uncovered statement, a citation
   to an excluded or unknown reference, a grade not printed in the cited guideline, a
  second-review disagreement without an outcome. Fix the
   working files and re-run. It writes the evidence table (`.csv` + `.xlsx`), the
   traceability matrix (`.csv`, and Markdown for the appendix) and appends the register
   row (never kept in the skill directory, which is replaced on plugin updates).

7. **Write the review** following
   [`references/document_template.md`](references/document_template.md) as Markdown,
   then convert it with `md_to_docx.py` (house style from `assets/reference.docx`, no
   tokens spent; see the shared procedure). Build the reference list with
   `format_references.py`; run `ledger_to_exports.py` for `.bib` + PMIDs.

8. **Hand over:** counts per verdict, the most important and any safety-flagged changes,
   items left for MDT decision, references excluded during checking, and the file list.

## Timing log

Log stage boundaries with the shared timing script — one short command per boundary,
so the researcher can see where time and tokens go and compare plugin versions:

```bash
python "[skill-path]/../../shared/scripts/run_log.py" "<workspace>" start run --skill protocol-reviewer
python "[skill-path]/../../shared/scripts/run_log.py" "<workspace>" start <stage>
python "[skill-path]/../../shared/scripts/run_log.py" "<workspace>" end <stage> [--tokens N]
```

Stages, in order: `map` (reading and mapping the protocol), `checkpoint` (waiting for the researcher's confirmation), `search` (all parallel agents + merge), `verify`, `judge`, `second_review`, `tables`, `document`. For stages that dispatch an agent, pass the token usage the
agent reports on completion as `--tokens` when you have it. Close with `end run`, then run
`run_log.py "<workspace>" summary` and include its output at the end of the hand-over
message. The script never fails a run; if it warns, carry on.

## Non-negotiables

- **References come only from the verified ledger** — never type a PMID, DOI, title or
  author list yourself; never cite anything outside the ledger or in
  `excluded_references`.
- **Every guideline-backed statement carries its grade inline** (`grade.display`
  verbatim, written naturally, e.g. "(BTS Grade 1C)") and every factual claim a numbered
  citation.
- **Every recommendation in the document appears in the traceability matrix** — the
  document and `judgements.yaml` must agree.
- **Draft status is explicit:** DRAFT callout and transparency disclaimer always present.
- **UK framing:** MHRA status, NICE TAs, UK registries; flag commissioning implications.
- **Scope:** review and recommend — don't rewrite the protocol, and stay within its scope
  unless there is a clear patient-safety reason.
- **Invisible plumbing:** never mention YAML, ledgers or working files to the researcher.

## Transparency disclaimer fields

Plugin version (`[skill-path]/../../.claude-plugin/plugin.json`); model identifier as
you understand it plus configured tier, e.g. `claude-opus-5-5 (configured: opus, effort
high)`; search date (`metadata.search_date`); review date (today); verification
(`metadata.verification`); second review (judgements challenged / revised / for MDT
decision).

## If something is missing

- `md_to_docx.py` exits 3 (no pandoc even after install): build the `.docx` with the
  environment's Word-document capability; if there is none, deliver the `.md`.
- PyYAML missing: ask the researcher to `pip install pyyaml`. openpyxl missing: the CSVs
  are still written; mention `pip install openpyxl` for the `.xlsx`.
- PubMed connector missing and no ledger: explain the search tools need enabling first.
- The researcher uploaded guideline PDFs: read them as extra context alongside the ledger.
