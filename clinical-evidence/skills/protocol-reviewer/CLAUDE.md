# CLAUDE.md

Maintainer notes for this skill. The runtime instructions live in `SKILL.md`; this file
records design decisions for anyone editing the skill.

## What it is

Reviews an uploaded clinical protocol (PDF/Word) against current guidelines and recent
evidence and produces a draft, section-by-section review (`.md` + `.docx`) with graded
recommendations, plus Zotero exports and a row in the workspace evaluation register.

## Files

- `SKILL.md` — outcome, workflow, non-negotiables. Kept deliberately short: current
  models need goals, constraints and reasons, not step-by-step procedure.
- `references/document_template.md` — document structure, draft callout and disclaimer
  text.
- `assets/reference.docx` — house style (A4, Arial, navy headings, header/footer); used
  directly if pandoc is the conversion route, otherwise a style reference.
- `evals/evals.json` — test scenarios.

## Design decisions

- **Shared evidence procedure.** Discovery, independent verification, validation,
  reference formatting and exports are defined once in
  `../../shared/references/consumer_integration.md`; this skill follows it.
- **Search driven by the protocol.** The skill passes the protocol's concrete statements
  (doses, thresholds, timings) to `evidence-search`, so the evidence answers what the
  review actually has to test.
- **Verification before citation.** `reference-checker` re-reads every PMID from PubMed
  given identifiers only; `verify_references.py` cross-checks tolerantly and moves
  failures to `excluded_references`. `format_references.py` builds the list, so
  reference text is never retyped.
- **Native .docx.** Claude Desktop / Cowork create Word files directly; pandoc is an
  optional route, not a dependency.
- **Evaluation register** at `<workspace>/clinical-evidence-register.csv` — never in the
  skill directory (the plugin cache is replaced on update). 2.1.0 added the
  `references_excluded` column at the end.

## AI use policy (ISO 42001)

- **System:** the latest Claude Opus at maximum effort (version named in the plugin
  README), via Claude Cowork or Claude Code.
- **Intended use:** evidence synthesis to support protocol review; it does not make
  clinical decisions.
- **Oversight:** every output is a draft for appraisal by a consultant-level clinician
  and the approving MDT.
- **Transparency:** DRAFT callout; disclaimer with plugin version, model, sources,
  search/review dates and verification status; "Reviewed and approved by" field.
- **Traceability:** the evaluation register records each review's counts and outcome.
