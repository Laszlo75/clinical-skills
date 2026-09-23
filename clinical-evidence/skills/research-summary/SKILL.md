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

# Clinical Evidence Summary

Answer "what does the current evidence say about X?" with a draft evidence summary a
clinician can rely on for a journal club, teaching, a grant, a business case or a
protocol update: current UK and international guideline positions with their grades,
the important recent evidence, where sources conflict, what is emerging, and where the
gaps are — every claim cited from a verified reference list. If the researcher has
uploaded a protocol to review, that is `protocol-reviewer`'s job instead.

Write for clinicians at peer level: precise and direct. When the evidence is clear, say
so; when it is thin ("single-centre retrospective series only") or contested, say that
too. When guidelines disagree with each other, or a newer trial contradicts a guideline,
show both positions with their grades — the reader needs to see the tension, not have
it smoothed over.

Run on the latest Claude Opus at maximum effort (see the plugin README for the current
model; in Claude Cowork, choose it in the app and enable extended thinking).

## Paths

Paths in this skill are relative to its base directory (the folder holding this
SKILL.md). Commands run from the researcher's workspace, so write `[skill-path]` as that
absolute base directory, quoted, and `<workspace>` as the researcher's folder. Shared
scripts are in `[skill-path]/../../shared/scripts/`.

## Workflow

1. **Pin down the question.** From the request, identify the topic, population and the
   sub-questions a clinician would want answered. If the request is broad or ambiguous,
   confirm scope in one short exchange; otherwise proceed.

2. **Get a verified evidence base.** Follow
   [`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md):
   reuse or build the ledger (pass your sub-questions to `evidence-search`), have every
   reference independently re-read and cross-checked, then validate.

3. **Write the summary** following
   [`references/evidence_summary_template.md`](references/evidence_summary_template.md)
   (sections, callout and disclaimer text). Organise recent evidence by clinical
   sub-question, not paper by paper. Deliver:
   - `[Topic_Name]_Evidence_Summary_[Year].md` — editable source;
   - `[Topic_Name]_Evidence_Summary_[Year].docx` — made with the environment's built-in
     Word document capability in the house style (A4, Arial, navy headings, title page,
     header/footer with title and page numbers). If pandoc is available instead,
     `pandoc … --reference-doc="[skill-path]/assets/reference.docx"` produces the same
     style;
   - `[Topic_Name]_References.bib` and `[Topic_Name]_PMIDs.txt` — from
     `ledger_to_exports.py`, same prefix.

4. **Hand over:** a few sentences on the headline findings, anything excluded during
   reference checking, and where the four files are.

## Non-negotiables

- **References come only from the verified ledger.** Build the reference list from
  `format_references.py` output; never type a PMID, DOI, title or author list yourself,
  never cite anything outside the ledger or in `excluded_references`. Plausible
  identifiers from memory are the classic failure in this domain.
- **Every guideline-backed statement carries its grade inline**, using `grade.display`
  verbatim (e.g. "NICE Strength: Strong"). Every factual claim has a numbered citation
  `[n]`, and every listed reference is cited.
- **Draft status is explicit:** the DRAFT — NOT FOR CLINICAL USE callout and the
  transparency disclaimer from the template are always present.
- **UK framing:** MHRA (not FDA) regulatory status, NICE technology appraisals, UK
  registries (NHSBT, UKRR…), and where UK practice differs from US/European practice.
- **Preprints are labelled** "(preprint, not peer-reviewed)" wherever cited.
- **Invisible plumbing:** never mention YAML, the ledger or file paths to the researcher,
  in chat or in the document.

## Transparency disclaimer fields

- plugin version — from `[skill-path]/../../.claude-plugin/plugin.json`;
- model identifier — the model you are running on as you understand it plus the
  configured tier, e.g. `claude-opus-5-5 (configured: opus, effort max)`;
- search date — `metadata.search_date`; document date — today (ISO 8601);
- verification — `metadata.verification` (independent second reading, date).

## If something is missing

- No Word-document capability and no pandoc: deliver the `.md` and say how to convert it.
- PyYAML missing: ask the researcher to `pip install pyyaml`; don't check by eye.
- PubMed connector missing and no ledger: explain the search tools need enabling first.
