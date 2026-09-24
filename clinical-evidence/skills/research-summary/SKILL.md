---
name: research-summary
model: opus
effort: high
description: >
  Clinical literature search and narrative evidence summary. Searches guidelines
  (NICE, BTS, KDIGO…), PubMed and Scholar Gateway, independently verifies every
  reference, and writes a draft evidence summary (.md + .docx) with Zotero exports
  (.bib + PMID list): guideline positions with grades, recent evidence, conflicts,
  emerging evidence and gaps. Use when the user asks for a literature search, evidence
  review or summary, narrative literature review, or reference list, or asks what the
  latest evidence or guidelines say on a clinical topic — e.g. "search PubMed for…",
  "find evidence on…", "what does NICE say about X?", "I'm updating our CMV protocol,
  what's the current thinking?". If the user has uploaded a protocol to review, use
  protocol-reviewer instead.
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

Run on the latest Claude Opus at high effort (see the plugin README for the current
model; in Claude Cowork, choose it in the app). The lead works economically: bulky
reading (abstracts, full texts, guideline pages) happens inside the search agents, which
run in parallel; this conversation sees only their short summaries.

## Paths

- This plugin's folder: `${CLAUDE_PLUGIN_ROOT}` — shared scripts in
  `${CLAUDE_PLUGIN_ROOT}/shared/scripts/`.
- This skill's folder: `${CLAUDE_SKILL_DIR}` — templates and assets.
- Guideline cache (kept between runs and plugin updates):
  `${CLAUDE_PLUGIN_DATA}/guideline_cache`. If that still reads as a placeholder, use
  `~/.clinical-evidence/guideline_cache`.
- `<workspace>` is the researcher's own folder — the one they selected or shared, where
  their protocol is and where the outputs are saved. In Cowork this is a mounted folder,
  **not** the shell's home or starting directory (e.g. not `/home/claude`): working
  files written there are invisible to the researcher and lost after the session. Use
  its absolute path and quote it.

The commands below and in the shared reference files use these two folders. If the two
folders above still read as placeholders rather than real paths, use the absolute path
of the folder holding this SKILL.md, and the plugin folder two levels above it.

## Workflow

1. **Pin down the question.** From the request, identify the topic, population and the
   sub-questions a clinician would want answered. If the request is broad or ambiguous,
   confirm scope in one short exchange; otherwise proceed.

2. **Get a verified evidence base.** Follow
   [`../../shared/references/consumer_integration.md`](../../shared/references/consumer_integration.md):
   reuse the ledger, or run 1–2 `guideline-search` agents (split by guideline body)
   alongside one `evidence-search` agent per cluster of 2–3 sub-question clusters, in parallel,
   then merge; check the references' identifiers (a quick PubMed ID conversion) and
   validate. Quote only guideline grades the validator confirmed in the source text.

3. **Write the summary** following
   [`references/evidence_summary_template.md`](references/evidence_summary_template.md)
   (sections, callout and disclaimer text). Organise recent evidence by clinical
   sub-question, not paper by paper. Deliver:
   - `[Topic_Name]_Evidence_Summary_[Year].md` — editable source;
   - `[Topic_Name]_Evidence_Summary_[Year].docx` — converted from the Markdown with
     `md_to_docx.py` (house style from `assets/reference.docx`, no tokens spent);
   - `[Topic_Name]_References.bib` and `[Topic_Name]_PMIDs.txt` — from
     `ledger_to_exports.py`, same prefix.

4. **Hand over:** a few sentences on the headline findings, anything excluded during
   reference checking, and where the four files are.

## Timing log

Log stage boundaries with the shared timing script — one short command per boundary,
so the researcher can see where time and tokens go and compare plugin versions:

```bash
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/run_log.py" "<workspace>" start run --skill research-summary
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/run_log.py" "<workspace>" start <stage>
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/run_log.py" "<workspace>" end <stage> [--tokens N]
```

Stages, in order: `search` (all parallel agents + merge), `verify`, `document` (writing the summary, `.docx` and exports). For stages that dispatch an agent, pass the token usage the
agent reports on completion as `--tokens` when you have it. Close with `end run`, then run
`run_log.py "<workspace>" summary` and include its output at the end of the hand-over
message. The script never fails a run; if it warns, carry on.

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

- plugin version — from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`;
- model identifier — the model you are running on as you understand it plus the
  configured tier, e.g. `claude-opus-5-5 (configured: opus, effort high)`;
- search date — `metadata.search_date`; document date — today (ISO 8601);
- verification — `metadata.verification` (independent second reading, date);
- guidelines — number read in this run and number reused from the cache, with the
  oldest `cached_on` date.

## If something is missing

- `md_to_docx.py` exits 3 (no pandoc even after install): build the `.docx` with the
  environment's Word-document capability; if there is none, deliver the `.md`.
- PyYAML missing: ask the researcher to `pip install pyyaml`; don't check by eye.
- PubMed connector missing and no ledger: explain the search tools need enabling first.
