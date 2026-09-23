# CLAUDE.md

Maintainer notes for this skill. The runtime instructions live in `SKILL.md`; this file
records design decisions for anyone editing the skill.

## What it is

The user-facing entry point for "what does the evidence say about X". Builds (or reuses)
a verified evidence base and writes a draft narrative evidence summary (`.md` + `.docx`)
plus Zotero exports (`.bib` + PMID list). It absorbed the former `literature-search`
skill's triggers in 2.0.0.

## Files

- `SKILL.md` — outcome, workflow, non-negotiables. Kept deliberately short: current
  models need goals, constraints and reasons, not step-by-step procedure.
- `references/evidence_summary_template.md` — document structure, draft callout and
  disclaimer text.
- `assets/reference.docx` — house style (A4, Arial, navy headings, header/footer); used
  directly if pandoc is the conversion route, otherwise a style reference.
- `evals/evals.json` — test scenarios.

## Design decisions

- **Shared evidence procedure.** Discovery, independent verification, validation,
  reference formatting and exports are defined once in
  `../../shared/references/consumer_integration.md`; this skill follows it.
- **Verification before citation.** `reference-checker` re-reads every PMID from PubMed
  given identifiers only; `verify_references.py` cross-checks tolerantly and moves
  failures to `excluded_references`. `format_references.py` builds the list, so
  reference text is never retyped.
- **Native .docx.** Claude Desktop / Cowork create Word files directly; pandoc is an
  optional route, not a dependency.
- **Honest labelling.** The document calls itself a "structured literature review", not a
  systematic review — there is no PRISMA-level search log yet (planned for v3).

## AI use policy (ISO 42001)

- **System:** the latest Claude Opus at maximum effort (version named in the plugin
  README), via Claude Cowork or Claude Code.
- **Intended use:** narrative synthesis of clinical evidence; it does not make clinical
  decisions.
- **Oversight:** every output is a draft that a clinician must appraise before use.
- **Transparency:** DRAFT callout; disclaimer with plugin version, model, sources,
  search/document dates and verification status; "Reviewed and approved by" field.
