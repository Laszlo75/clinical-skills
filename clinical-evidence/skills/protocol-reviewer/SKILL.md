---
name: protocol-reviewer
model: opus
effort: max
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

Run on the latest Claude Opus at maximum effort (see the plugin README for the current
model; in Claude Cowork, choose it in the app and enable extended thinking).

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
   Pass the confirmed questions (ids and text) to `evidence-search` so it tags each
   source with the questions it answers and records study design, population, size and
   certainty. For more than ~4 questions, dispatch several agents in parallel, each with a
   cluster of questions and its own output file, then combine them with
   `merge_ledgers.py` before verification.

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
   grade (`grade.display` verbatim), confidence (high/moderate/low), and flags for patient
   safety and commissioning impact. Weigh conflicting sources explicitly.

5. **Second review.** Dispatch the `second-reviewer` agent with the paths to the map,
   the judgements and the ledger, and `.clinical-evidence/second_review.yaml` as its
   output. For every `disagree` or `unsupported`, either revise the judgement or keep it
   and write why; record this in each judgement's `second_review` (status, note,
   resolution). Add judgements for any `missing` issues it raises that you agree with.

6. **Build the tables and register row:**

   ```bash
   python "[skill-path]/../../shared/scripts/review_tables.py" \
     --ledger "<workspace>/.literature_search_ledger.yaml" \
     --map "<workspace>/.clinical-evidence/protocol_map.yaml" \
     --judgements "<workspace>/.clinical-evidence/judgements.yaml" \
     --prefix "[Protocol_Name]" --outdir "<workspace>" \
     --register "<workspace>/clinical-evidence-register.csv" \
     --model-id "<model id (configured: opus, effort max)>" --skill-version "<plugin version>"
   ```

   It refuses to build if anything is inconsistent — an uncovered statement, a citation
   to an excluded or unknown reference, an unresolved second-review disagreement. Fix the
   working files and re-run. It writes the evidence table (`.csv` + `.xlsx`), the
   traceability matrix (`.csv`, and Markdown for the appendix) and appends the register
   row (never kept in the skill directory, which is replaced on plugin updates).

7. **Write the review** following
   [`references/document_template.md`](references/document_template.md): `.md` source
   plus `.docx` in the house style (A4, Arial, navy headings, title page, header/footer),
   made with the environment's Word-document capability — or pandoc with
   `[skill-path]/assets/reference.docx` if that's what's available. Build the reference
   list with `format_references.py`; run `ledger_to_exports.py` for `.bib` + PMIDs.

8. **Hand over:** counts per verdict, the most important and any safety-flagged changes,
   second-review disagreements you kept, references excluded during checking, and the
   file list.

## Non-negotiables

- **References come only from the verified ledger** — never type a PMID, DOI, title or
  author list yourself; never cite anything outside the ledger or in
  `excluded_references`.
- **Every guideline-backed statement carries its grade inline** (`grade.display`
  verbatim) and every factual claim a numbered citation.
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
max)`; search date (`metadata.search_date`); review date (today); verification
(`metadata.verification`); second review (number of judgements challenged / revised).

## If something is missing

- No Word-document capability and no pandoc: deliver the `.md` and say how to convert it.
- PyYAML missing: ask the researcher to `pip install pyyaml`. openpyxl missing: the CSVs
  are still written; mention `pip install openpyxl` for the `.xlsx`.
- PubMed connector missing and no ledger: explain the search tools need enabling first.
- The researcher uploaded guideline PDFs: read them as extra context alongside the ledger.
