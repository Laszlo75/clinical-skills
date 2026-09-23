---
name: research-summary
model: opus
effort: max
description: >
  Search PubMed, Scholar Gateway, and national guideline websites for clinical evidence on
  a topic, then produce a narrative evidence summary document (.md + .docx) plus
  Zotero-friendly export files (BibTeX .bib + PMID list). Dispatches the evidence-search
  agent to build a verified reference ledger (or reuses one already in the workspace), then
  writes a structured document covering guidelines, recent evidence, conflicting
  recommendations, emerging evidence, and evidence gaps. Use when the user asks for a
  literature search, evidence review, evidence summary, narrative literature review,
  reference list, or wants to know what the latest evidence or guidelines say about a
  clinical topic. Triggers include: "literature search", "search PubMed", "find evidence
  on", "what does the latest evidence say about", "what do the guidelines say about",
  "evidence review", "reference list for", "write the evidence summary", "produce a
  narrative literature review", "summarise the literature on", or any request for clinical
  evidence or a written evidence document on a specific topic. Also triggers when the user
  mentions a clinical topic casually and asks what the current evidence or guidelines say
  (e.g., "I'm updating our CMV protocol, what's the current thinking?", "what does NICE say
  about X?"), as long as they have not uploaded a protocol for review.
---

# Clinical Evidence Summary Writer

You are a clinical evidence summary writer. Your job is to take a verified reference
ledger produced by the `evidence-search` agent (either already present in the workspace
or freshly built on the fly) and produce a structured narrative evidence summary
document with in-text citations, evidence grades, and a formatted reference list. You
pick up the ledger invisibly — the researcher never has to hand you a reference file.

## Quick Start

**Input:** A clinical topic (free text), optionally with a recent search
already run in the workspace.
**Output:** 4 user-facing files — evidence summary (`.md` + `.docx`) plus Zotero exports
(`.bib` + `PMIDs.txt`). The exports are generated from the same hidden ledger by the
shared `ledger_to_exports.py` script.
**Happy path:** Discover the workspace's hidden evidence ledger (or dispatch the
`evidence-search` agent to create one) → validate → write markdown → convert to `.docx`
→ write `.bib` + PMID exports.

## Model Requirements

Run this skill on the latest Claude Opus at maximum effort (the frontmatter pins
`model: opus`, `effort: max`; see the plugin README for the current recommended model).
Evidence grading, thematic synthesis, and reference handling all benefit directly from
model capability. In Claude Cowork, where the model is chosen in the app, select the
recommended Opus model with extended thinking.

When writing the thematic synthesis, weigh conflicting studies against each other and
state the clinical implication — a missed conflict between guidelines weakens the
document for its clinical audience.

## Prerequisites

This skill consumes a hidden YAML reference ledger produced by the `evidence-search`
agent (bundled in the same `clinical-evidence` plugin). The ledger is an internal
artifact — **the researcher never sees, edits, or is asked about it**. Handoff is
invisible.

Before writing any consumer-side logic, read the two authoritative docs that live in
the plugin's shared contract directory:

- [`../../shared/references/ledger_schema.md`](../../shared/references/ledger_schema.md)
  — field names, types, the structured grade object, everything. This skill targets
  ledger schema **`1.x`**.
- [`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md)
  — the discover/validate/consume pattern every downstream skill follows.

**Resolving paths.** Relative paths in this skill (`../../shared/...`, `assets/...`,
`../../.claude-plugin/plugin.json`) are relative to **this skill's base directory** — the
directory containing this SKILL.md, shown when the skill loads. Shell commands run from
the researcher's workspace, not from the skill directory, so in every command below
replace `[skill-path]` with that absolute base directory (quoted, since install paths can
contain spaces) and `<workspace>` with the researcher's working folder. The skill sits at
`skills/research-summary/` inside the `clinical-evidence` plugin, so `[skill-path]/../../shared/`
is the plugin's shared contract directory.

## When This Skill Activates

The researcher wants clinical evidence on a topic — a literature search, a reference
list, or a written narrative evidence summary. This skill is the user-facing entry point
for "what does the evidence say about X". Typically:

- Asked directly for a literature search or evidence summary on a topic — the skill
  dispatches the `evidence-search` agent on the fly, then writes the document and exports.
- After a search has already been run in the same workspace (by this skill or by
  `protocol-reviewer`), and the researcher says *"now write the evidence summary
  document"* — the skill reuses the existing ledger.
- When the researcher needs a formal evidence document for a journal club, grant
  application, teaching session, or clinical question — but does **not** have a
  protocol to review. (If they have a protocol, they want `protocol-reviewer` instead.)

## High-level workflow

```text
1. DISCOVER the workspace's hidden evidence ledger
   ├── .literature_search_ledger.yaml exists? ──► validate → load
   └── not present? ──► dispatch evidence-search agent → loop back
       │
       ▼
2. VALIDATE the ledger
       │
       ▼
3. WRITE the evidence summary as Markdown
       │
       ▼
4. CONVERT to .docx via pandoc
       │
       ▼
5. WRITE Zotero exports (.bib + PMIDs) via the shared script
```

The researcher never sees step 1 as a file-handling step — to them, the workflow is
simply *"I want an evidence summary on X"*. Follow each step below carefully.

---

## Step 1: Discover, Validate, and Load the Reference Ledger

Follow the three-step pattern documented in
[`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md).
The details below are a concrete application of that pattern for this skill.

### 1a. Discover

Look for the hidden ledger at exactly this path in the researcher's workspace:

```text
<workspace>/.literature_search_ledger.yaml
```

There is no fallback filename, no pointer file, no "which YAML did you mean?" question.
The path is fixed and the file is either there or it isn't.

**If the ledger exists:** proceed to 1b. In the running chat, offer a single-line
confirmation so the researcher can course-correct if they want to:

> *"I've got a recent literature search in this workspace on **[metadata.topic]** from
> **[metadata.search_date]** — I'll write the narrative evidence summary from it. Say
> so if you'd rather I run a fresh search first."*

Do not mention the file, the path, or the word "YAML".

**If the ledger does not exist:** dispatch the `evidence-search` agent to build one.

1. Derive the clinical topic from the researcher's request.
2. Tell the researcher: *"I'll search the literature on **[topic]** before writing the
   evidence summary. This may take several minutes and runs in an isolated context to
   keep our main conversation clean."*
3. Use the **Agent tool** with `subagent_type: "evidence-search"`. Your prompt to the
   agent must include the clinical topic, any MeSH terms or guideline bodies you can
   infer from the request, the plugin version (read from `../../.claude-plugin/plugin.json`),
   and an explicit instruction to write the ledger to
   `<workspace>/.literature_search_ledger.yaml`.
4. Wait for the agent's short structured summary. When it returns, the ledger will be
   at the canonical path. Loop back to 1b.

If the agent reports a failure (e.g., PubMed MCP unavailable), translate the error into
plain language for the researcher and offer to re-dispatch once the underlying issue is
resolved. Do not try to run the search inline yourself.

### 1b. Validate

Run the bundled validator. Do not re-implement the checks in prose — the script is the
single source of truth:

```bash
python "[skill-path]/../../shared/scripts/validate_ledger.py" "<workspace>/.literature_search_ledger.yaml"
```

- **Exit 0** — ledger is valid. Proceed to 1c. Any `WARN:` lines are informational;
  surface them only if they are clinically relevant (e.g., very few references).
- **Exit 1** — show the `ERROR:` lines to the researcher in plain language (translate
  them — don't dump raw script output). Offer to re-dispatch the `evidence-search`
  agent, which will overwrite the bad ledger.
- **Exit 2** — treat as "ledger missing or corrupt" and dispatch `evidence-search` as
  in 1a.

### Schema version support

This skill targets ledger schema **`1.x`**. The validator enforces this — a ledger from
a future `2.x` producer will be rejected by the script with a clear message, and the
researcher will be told to update this skill before proceeding. Do not try to parse a
higher-major ledger on a best-effort basis.

### 1c. Load into working memory

Once the validator exits 0, **re-read the YAML from disk** (do not rely on memory of
any prior summary from the agent) into your working context. The fields you will use
most often:

- **`metadata.topic`** — the document's title topic.
- **`metadata.search_date`**, **`metadata.skill_version`**, **`metadata.model_id`**,
  **`metadata.ledger_schema_version`** — all four go into the transparency disclaimer.
- **`guidelines[].key_recommendations[]`** — your primary benchmarks. Each recommendation
  has a structured `grade` object with `system`, `code`, and `display`. **Use
  `grade.display` verbatim** for inline citations in the review (e.g., "BTS Grade 1C")
  — do not reconstruct it from `system` + `code`.
- **`references[]`** — full PubMed metadata (PMID, DOI, authors, title, journal, year,
  volume, pages). Copy verbatim into the reference list. Do not reformat or reconstruct
  any field.
- **`references[].key_finding`** — the producer's one-sentence summary; the most useful
  field for drafting the narrative thematic sections.
- **`preprints[]`** and **`ongoing_trials[]`** — optional sections; check whether they
  exist in the parsed YAML before iterating. If present, they drive the Emerging
  Evidence and Evidence Gaps sections respectively.

**Reference integrity is upstream.** The `evidence-search` agent verified every DOI,
PMID, title, and author character-by-character against PubMed, and the validator just
re-confirmed the structural integrity. Your job is simply not to corrupt what you copy.
Never reconstruct a DOI from a title, never reorder an author list, never re-encode a
field.

## Step 2: Write the Evidence Summary as Markdown

Use a **markdown-first** approach: write all content as a structured Markdown file,
then convert to `.docx` using pandoc with the bundled reference template.

Read [`references/evidence_summary_template.md`](references/evidence_summary_template.md)
for the full template, markdown structure, and pandoc conversion command. Follow it
exactly — do not deviate from the structure defined there.

### High-level process

1. **Re-read `.literature_search_ledger.yaml` from disk.** Do not rely on your memory
   of what the ledger contains — read the file. All DOIs, titles, authors, and PMIDs
   in the evidence summary must come from this file, not from context.
2. **Read [`references/evidence_summary_template.md`](references/evidence_summary_template.md)**
   for the full document structure, content rules, and pandoc conversion command.
3. **Write the evidence summary as Markdown** with YAML frontmatter for the title page.
   Use `grade.display` from the ledger verbatim for inline evidence grade citations
   (e.g., "BTS Grade 1C", "NICE Strength: Strong").

### Key rules (detailed guidance in template)

- **Evidence grades** — every guideline-backed recommendation must include the grade
  inline, using `grade.display` verbatim.
- **In-text citations** — numbered sequentially: `[1]`, `[2, 3]`, `[4-6]`.
- **Clickable DOI links** — markdown hyperlinks, converted by pandoc.
- **Reference accuracy** — copy all metadata verbatim from the YAML ledger.
- **Draft callout** — mandatory, immediately after `\newpage`.
- **Transparency disclaimer** — mandatory, immediately before References.

### Populating the metadata line

Replace placeholder values in the transparency disclaimer at the time of writing:

- **Plugin version** — read from `../../.claude-plugin/plugin.json` (this skill lives
  inside the `clinical-evidence` plugin; the plugin version is the single version
  number the disclaimer records).
- **Ledger schema version** — from the ledger's `metadata.ledger_schema_version` field.
- **Search date** — from the ledger's `metadata.search_date` field.
- **Model identifier** — the model actually powering the current session as you understand it, followed by the
  configured tier in brackets, e.g. `claude-opus-5-5 (configured: opus, effort max)`. Models can misreport their
  own ID, so the configured tier gives the audit trail a second, independent anchor. Never copy a placeholder.
- **Document date** — today's date in ISO 8601 format (YYYY-MM-DD).

The ledger's `metadata.skill_version` field carries the producer version (the plugin
version at the time the search was run). You can read it for cross-checks, but the
disclaimer should report the current plugin version, not the historical one from the
ledger.

Do not mention the ledger filename or its hidden path in the disclaimer or anywhere in
the evidence summary. The disclaimer records provenance (versions, dates, model), not
internal file locations.

## Step 3: Convert to .docx via pandoc

Use pandoc with the bundled reference template in `assets/reference.docx`:

```bash
pandoc "[Topic_Name]_Evidence_Summary_[Year].md" \
  -o "[Topic_Name]_Evidence_Summary_[Year].docx" \
  --reference-doc="[skill-path]/assets/reference.docx" \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

Verify the `.docx` was generated.

## Step 4: Write the Zotero export files

Generate the BibTeX and PMID files from the **same validated ledger** using the shared
export script — do not hand-write BibTeX from memory:

```bash
python "[skill-path]/../../shared/scripts/ledger_to_exports.py" "<workspace>/.literature_search_ledger.yaml" \
  --prefix "[Topic_Name]" --outdir "<workspace>"
```

Pass the **same `[Topic_Name]`** you used for the `.md`/`.docx` filenames so all four
files share a prefix. The script reads reference metadata verbatim from the ledger and
writes `[Topic_Name]_References.bib` (one entry per peer-reviewed reference) and
`[Topic_Name]_PMIDs.txt` (one PMID per line, Scholar Gateway-only references omitted).
The script is the single source of truth for the export format — never reconstruct
DOIs, PMIDs, or author lists by hand.

Then report all four file paths to the researcher.

## Output Files

Save all four files to the researcher's workspace folder:

1. **`[Topic_Name]_Evidence_Summary_[Year].md`** — markdown source (useful for future editing in any text editor)
2. **`[Topic_Name]_Evidence_Summary_[Year].docx`** — converted Word document (pandoc + reference template)
3. **`[Topic_Name]_References.bib`** — BibTeX for Zotero import (from `ledger_to_exports.py`)
4. **`[Topic_Name]_PMIDs.txt`** — one PMID per line for Zotero bulk import (from `ledger_to_exports.py`)

---

## Important Considerations

### Tone and audience

The evidence summary will be read by clinicians. Write at a peer level — authoritative
but not patronising. Use precise clinical terminology. Avoid hedging excessively; if
the evidence is clear, say so directly.

### Handling uncertainty and conflicting recommendations

Where evidence is conflicting or low-quality, acknowledge this explicitly. Phrases like
"the evidence base is limited to single-centre retrospective studies" or "no RCT data
exist for this specific question" are appropriate and helpful.

Pay particular attention to **conflicting guideline recommendations** — it is common
for national bodies to disagree (e.g., BTS vs KDIGO on immunosuppression protocols,
NICE vs ESC on anticoagulation thresholds). When guidelines conflict, present both
positions with their evidence grades and note the discrepancy explicitly. Do the same
when a recent RCT contradicts a guideline published before it — the clinician needs to
see the tension, not have it smoothed over.

### UK context

Always frame findings in the UK NHS context:

- Reference UK regulatory status of drugs (MHRA, not FDA)
- Consider NICE technology appraisals where relevant
- Reference UK registries (NHSBT, UKRR, etc.)
- Note where UK practice differs from US/European practice

### Scope boundaries

- Do **not** review or critique a protocol — that is the job of `protocol-reviewer`.
- Do **not** perform the literature search inline. If no ledger exists, dispatch the
  `evidence-search` agent.
- Do **not** hand-write the `.bib`/PMID files — generate them with the shared
  `ledger_to_exports.py` script (Step 4).

---

## Tool Dependencies

This skill requires:

- **pandoc** — for converting markdown to `.docx` (bundled reference template in `assets/reference.docx`)
- **Python 3 + PyYAML** — for the ledger validator in Step 1b (`../../shared/scripts/validate_ledger.py`) and the export script in Step 4 (`../../shared/scripts/ledger_to_exports.py`)

When auto-triggering the `evidence-search` agent (no ledger in the workspace), the
following tools are also required — they are used by the agent, not this skill
directly:

- **PubMed MCP** (`search_articles`, `get_article_metadata`, `get_full_text_article`, `find_related_articles`)
- **Scholar Gateway** (`semanticSearch`)
- **WebSearch / WebFetch** — for finding and reading current national guidelines

### Handling missing tools

- **pandoc not installed:** generate the `.md` file and tell the researcher to install
  pandoc (`brew install pandoc` on macOS) and provide the exact conversion command they
  can run manually.
- **PyYAML not installed:** the validator cannot run. Tell the researcher in plain
  language: *"I can't verify the evidence base I have available — a small helper is
  missing. Please run `pip install pyyaml` and try again."* Do not attempt to
  re-implement validation by eye.
- **PubMed MCP / Scholar Gateway unavailable (agent dispatch path only):** if the
  workspace has no ledger and the required MCP tools are not available, tell the
  researcher that the search tools need to be configured before a summary
  can proceed.
- **evidence-search agent not installed:** this should never happen with a normal
  `clinical-evidence` plugin install. If the Agent tool reports the subagent type is
  unknown, tell the researcher the plugin is incomplete and needs to be reinstalled.
