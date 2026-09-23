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

Take an existing clinical protocol, test what it says against current UK and
international guidelines and the best recent evidence, and produce a draft review a
consultant-led MDT can act on: section by section, what is still right, what needs
changing, and why — with graded, verified citations.

The reader is a consultant-level clinician. Write at peer level: precise, direct, no
over-hedging. Where the evidence is weak or conflicting, say so plainly ("no RCT data
exist for…", "BTS and KDIGO differ on…"), and say when the protocol is already aligned —
that reassurance is useful too.

Run on the latest Claude Opus at maximum effort (see the plugin README for the current
model; in Claude Cowork, choose it in the app and enable extended thinking).

## Paths

Paths in this skill are relative to its base directory (the folder holding this
SKILL.md). Commands run from the researcher's workspace, so write `[skill-path]` as that
absolute base directory, quoted, and `<workspace>` as the researcher's folder. Shared
scripts are in `[skill-path]/../../shared/scripts/`.

## Workflow

1. **Understand the protocol.** Read it in full: title, version and date, clinical
   domain, population, and every concrete statement that could be out of date — drugs
   and doses, thresholds and targets, timings, procedures, monitoring — plus the age of
   its own references. Summarise your understanding to the researcher in 3–4 sentences
   so they can correct it, and check population scope if unclear (e.g. adult and
   paediatric).

2. **Get a verified evidence base.** Follow
   [`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md):
   reuse or build the ledger, have every reference independently re-read and
   cross-checked, then validate. When dispatching `evidence-search`, pass the specific
   statements from step 1 that need testing, not just the topic — that is what makes
   the search useful for a review.

3. **Cross-reference.** For each protocol section, compare what it says with the
   guideline position (with grade) and the recent evidence, then classify it:

   | Classification | Meaning |
   |---|---|
   | Aligned | Matches current guidelines and evidence; no change needed |
   | Minor update | Approach sound; wording, dose or detail needs adjusting |
   | Major update | Guidelines or evidence now support a materially different practice |
   | New addition | Not covered, but should be |
   | Remove | Outdated or no longer recommended |

   Give each finding a clear, actionable recommendation. Weigh conflicting sources
   explicitly rather than smoothing them over; think about the patient-safety
   consequence of each change.

4. **Write the review** following
   [`references/document_template.md`](references/document_template.md) (structure,
   callout and disclaimer text). Deliver:
   - `[Protocol_Name]_Review_[Year].md` — editable source;
   - `[Protocol_Name]_Review_[Year].docx` — made with the environment's built-in Word
     document capability in the house style (A4, Arial, navy headings, title page,
     header/footer with title and page numbers). If pandoc is available instead,
     `pandoc … --reference-doc="[skill-path]/assets/reference.docx"` produces the same
     style;
   - `[Protocol_Name]_References.bib` and `[Protocol_Name]_PMIDs.txt` — from
     `ledger_to_exports.py`.

5. **Log to the evaluation register** (below), then tell the researcher: counts per
   classification, the most important changes, and where the files are.

## Non-negotiables

- **References come only from the verified ledger.** Build the reference list from
  `format_references.py` output; never type a PMID, DOI, title or author list yourself,
  never cite anything outside the ledger or in `excluded_references`. Plausible
  identifiers from memory are the classic failure in this domain.
- **Every guideline-backed statement carries its grade inline**, using `grade.display`
  verbatim (e.g. "BTS Grade 1C"). Every factual claim has a numbered citation `[n]`.
- **Draft status is explicit:** the DRAFT — NOT FOR CLINICAL USE callout and the
  transparency disclaimer from the template are always present.
- **UK framing:** MHRA (not FDA) regulatory status, NICE technology appraisals, UK
  registries (NHSBT, UKRR…), and where UK practice differs from US/European practice.
  Flag anything that needs commissioner approval or a business case.
- **Scope:** review and recommend — don't rewrite the protocol, and don't stray beyond
  its scope unless there is a clear patient-safety reason.
- **Invisible plumbing:** never mention YAML, the ledger or file paths to the researcher,
  in chat or in the document.

## Transparency disclaimer fields

Fill these when writing section 6 of the template:

- plugin version — from `[skill-path]/../../.claude-plugin/plugin.json`;
- model identifier — the model you are running on as you understand it plus the
  configured tier, e.g. `claude-opus-5-5 (configured: opus, effort max)` (models can
  misreport their own ID; the configured tier is a second anchor);
- search date — `metadata.search_date`; review date — today (ISO 8601);
- verification — `metadata.verification` (independent second reading, date).

## Evaluation register

Append one row to `<workspace>/clinical-evidence-register.csv` (create it with this
header if absent). It lives in the researcher's folder — never in the skill directory,
which is replaced on every plugin update. It is the clinician's audit trail and reads
straight into R.

```text
review_date,protocol_name,protocol_version,clinical_domain,skill_version,model_id,total_references,guidelines_consulted,recommendations_aligned,recommendations_minor_update,recommendations_major_update,recommendations_new_addition,recommendations_remove,references_excluded,mdt_outcome,appraiser,notes
```

`guidelines_consulted` is semicolon-separated (e.g. `BTS 3rd Ed 2016;KDIGO 2024`),
`references_excluded` is the number removed by verification, and `mdt_outcome`,
`appraiser` and `notes` stay blank for the clinician. If an existing register has the
older header without `references_excluded`, keep its columns and add the new one at the
end rather than rewriting history.

## If something is missing

- No Word-document capability and no pandoc: deliver the `.md` and say how to convert it.
- PyYAML missing: ask the researcher to `pip install pyyaml`; don't check by eye.
- PubMed connector missing and no ledger: explain the search tools need enabling first.
- Researcher uploaded guideline PDFs: read them as extra context alongside the ledger.
