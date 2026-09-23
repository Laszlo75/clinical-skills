# clinical-evidence v3 — review findings and workflow design

> **Status (2026-09-23):** Phase 0 shipped as v2.0.1, Phase 1 as v2.1.0 (+ 2.1.1 loader fix), Phase 2 (question-driven protocol review, second reviewer, evidence table, traceability matrix) as v2.2.0. Phase 1 made two changes to the design below, on the maintainer's feedback:
> - **Verification uses the PubMed MCP connector, not direct E-utilities/Crossref calls.** A `reference-checker` agent makes an independent second reading and `verify_references.py` compares the two readings tolerantly.
> - **pandoc and citeproc are dropped as dependencies.** Claude Desktop/Cowork create `.docx` natively, the model numbers citations, and `format_references.py` generates the reference list.
>
> A third principle now applies throughout: prompts state outcomes, constraints and reasons, not step-by-step procedure, because current models need less hand-holding. The sections below keep the original design for context. Where they mention E-utilities probes or citeproc rendering, the notes above supersede them.

## Context

The user asked for a critical review of the `clinical-evidence` plugin (v2.0.0: `research-summary`, `protocol-reviewer` and the `evidence-search` agent) and for a move to **Opus 5.5 at max effort**. After the first review, they asked two further things:
- Rethink the **whole workflow**: how would I design protocol review from scratch today?
- Make **reference verification tolerant** of harmless differences between sources, such as author/title spelling, diacritics and punctuation.

Intended outcome: a v3 design that
- traces every protocol statement through to its evidence and a verdict,
- takes bibliographic metadata straight from the source databases instead of relying on the model to copy it,
- checks references with tolerant matching instead of exact string comparison,
- adds an independent second-reviewer pass that checks the substance (does the cited paper actually support the claim?),
- keeps what already works well: the handoff the researcher never sees, Markdown → pandoc `.docx`, the DRAFT callouts and ISO 42001 disclaimers, and the evaluation register.

## What is wrong with the current workflow (root causes, not symptoms)

1. **The model types bibliographic data, and then we check its typing.** In the agent, the model copies a DOI from the tool output into YAML "character by character", then re-fetches it and compares. That causes the typo risk and then patches over it. It also makes checking brittle, which is the user's point: PubMed and Crossref legitimately differ on diacritics, capitalisation, HTML tags in titles, journal abbreviations, and epub vs print year. **Fix: the model should only ever handle identifiers (PMID/DOI). A script fetches the metadata and the citation text is generated from it.**
2. **We check that references exist, which is the easy part.** The real clinical risk is a *real* paper cited for a claim it does not make, or a guideline dose paraphrased wrongly. At present nothing checks claim ↔ evidence support.
3. **The search is organised by topic, not by question.** The agent searches "ABOi transplantation" in general, and the reviewer maps references to sections afterwards using a one-line `key_finding`. You can't trace which protocol statement was tested against which evidence, and gaps go unnoticed.
4. **A single hidden ledger per workspace** means one topic, gets overwritten, and can be silently reused on the wrong topic.
5. **No record of the process:** no search log, no evidence table, no run manifest. That makes the "systematic" claim and ISO 42001 traceability weak.
6. **Operational bugs:**
   - The evaluation register is written inside the plugin cache, so it is wiped on update.
   - Script and asset paths are relative, but commands run from the workspace, so they break.
   - The agent is set to `model: inherit`, so it can run on a weaker model than the skills.
   - The evals have no fixtures and no assertions, so they can't be run.
   - The prose hard-codes "Opus 4.7".

## Proposed v3 workflow: one pipeline, two front-ends

```
 protocol (PDF/DOCX)                      topic / clinical question
        │                                            │
 [1] PROTOCOL MAP  (reviewer only)                    │
     sections → atomic statements                     │
     (drug, dose, threshold, timing, population)      │
        │                                            │
 [2] SCOPE + QUESTIONS  ◄──── checkpoint 1 (clinician confirms) ────┘
     PICO-style review questions; population; UK/intl jurisdiction
        │
 [3] RETRIEVE  (parallel evidence-search agents, one per question cluster)
     guidelines first (NICE → UK specialty body → international), then SR/MA → RCT → registry
     every query is logged automatically (database, string, date, hits, included)
        │
 [4] RECORD  (deterministic)
     fetch_metadata.py: PMID/DOI → PubMed E-utilities / Crossref → CSL-JSON
     the model adds the appraisal only: design, n, population, outcome, direction, certainty,
     plus a verbatim SUPPORTING PASSAGE and its location (abstract/full text/guideline section)
        │
 [5] VERIFY  (tolerant, scripted) ── verify_references.py → pass / review / fail per ref
        │
 [6] APPRAISE + JUDGE  (reviewer: per protocol statement; summary: per question)
     Aligned / Minor / Major / New / Remove + safety flag + confidence + commissioning flag;
     each judgement cites evidence IDs
        │
 [7] SECOND REVIEWER  (fresh-context verifier agent, adversarial)
     for each judgement: does the stored passage support it? dose vs BNF/SmPC?
     unsupported → downgraded or flagged, never silently kept
        │
 [8] RENDER
     Markdown with [@pmid:…] keys → render_citations.py (Vancouver) → pandoc → .docx
     + evidence table (.csv/.xlsx, R-friendly) + traceability matrix + .bib + PMIDs
        │
 [9] GOVERNANCE
     run manifest (model, effort, plugin version, input hashes, search log),
     evaluation register row in a stable user location
```

Key design choices:
- **Question-driven search.** Every protocol statement links to a question, which links to evidence, which leads to a verdict. The traceability matrix is itself a deliverable, and a missing link shows up as a gap.
- **A script renders the citations.** The model writes `[@pmid:29596116]`, and `render_citations.py` handles numbering, ordering and formatting from the verified records. This removes the whole "copy verbatim, number sequentially, cite every reference" class of errors.
- **Independent verifier agent.** This mirrors dual review in systematic reviews. It runs in a fresh context so it doesn't inherit the author's reasoning. It only sees the judgements and the stored passages.
- **Parallel retrieval.** Opus 5.5 handles fan-out and long contexts well. Searching per question in parallel makes it faster and more thorough, while the parent context stays clean.
- **Workspace store instead of a single hidden file:** `.clinical-evidence/<topic-slug>_<date>/` holding `ledger.yaml`, `refs.csl.json`, `search_log.csv`, `manifest.json` and `sources/` (cached guideline text). It supports several topics, keeps history, and allows reuse matched on topic plus freshness (older than 6 months → offer a refresh).
- **One clinician checkpoint:** scope and questions are confirmed before any evidence is gathered. The rest runs without stopping.

## Decisions from the user
- **Target runtime: Claude Cowork.**
- **Scope: phased v3.**
- **User-facing outputs to add:** evidence table (CSV + xlsx) and traceability matrix (as a docx appendix; also written as CSV).
- The verification report stays internal: it goes in the store, and only "review"/"fail" rows are summarised in chat.
- No verdict checkpoint. Checkpoint 1 (scope/questions) is the only interactive stop.

### What Cowork means for the design
- **Scripts probably have no outbound network.** Cowork's sandbox may block NCBI/Crossref unless the user allowlists them. So there are two metadata paths, tried in this order:
  1. **Direct fetch.** At startup, `fetch_metadata.py --probe` tests access to `eutils.ncbi.nlm.nih.gov` and `api.crossref.org`. If both are reachable, metadata is generated from source as designed. The README documents how to allowlist the two domains in Cowork.
  2. **Dual independent transcription (default fallback).**
     - The search agent records metadata from the PubMed MCP into `refs_a.yaml`.
     - The verifier agent, in a fresh context, re-fetches every PMID through the MCP and records it independently into `refs_b.yaml`.
     - `verify_references.py` compares A and B using the tolerant rules. A transcription error would have to happen identically twice, in two separate contexts, to get through.
     - This replaces "character-by-character" self-checking with a scripted comparison.
- **Don't depend on pandoc citeproc.** A small script, `render_citations.py`, replaces `[@pmid:…]` / `[@ref:…]` keys with Vancouver numbers in order of first citation, and builds the reference list from the verified records. It is deterministic and needs no pandoc filters.
  - For md → docx, use pandoc if it is present. Otherwise `pip install pypandoc_binary`, which bundles pandoc.
  - The xlsx is written with `openpyxl`, and a CSV is always written alongside it.
- **Persistence.** Cowork works inside a folder the user chose, and the VM home directory may not survive between sessions. So both the store and the evaluation register live in **that folder**:
  - store: `.clinical-evidence/`
  - register: `clinical-evidence-register.csv`, visible because it is the clinician's audit trail
- **Model selection.** Cowork may ignore the skill/agent `model:` frontmatter; the model is picked in the UI. Keep the frontmatter (`model: opus`, max effort) for Claude Code users. In the README, tell Cowork users to select Opus 5.5 with extended thinking. Verify during implementation what Cowork honours for plugin agents and skills.

## Tolerant verification spec (`shared/scripts/verify_references.py`)

Principle: **identifiers are hard anchors; descriptive fields are compared fuzzily and only used to catch a *wrong paper*, never to catch typos.** Once metadata is generated from the source records, typo-level mismatches can no longer occur.

| Check | Rule | Outcome |
|---|---|---|
| PMID resolves (E-utilities `esummary`) | must resolve | fail if not |
| DOI | normalise: strip `https://doi.org/`, trim, **case-insensitive** (DOIs are case-insensitive by spec) | PMID-record DOI ≠ ledger DOI → fail |
| DOI-only reference | Crossref `/works/{doi}` resolves | fail if 404 |
| Title | normalise: NFKC, casefold, strip HTML/MathML tags, punctuation, trailing period, bracketed translations; compare with token-set similarity (`rapidfuzz` if present, else `difflib`) | ≥0.90 pass · 0.75–0.90 review · <0.75 fail (likely wrong paper) |
| First author | surname only: strip diacritics (Müller=Muller=Mueller), hyphens/spaces, particles (van, de, von); initials ignored | match → pass; else review |
| Year | epub vs print | ±1 pass; otherwise review |
| Journal | compare NLM ID / ISSN if available; ignore abbreviation vs full-name differences | informational only |
| Retraction | PubMed publication type "Retracted Publication", or a Crossref `update-to` retraction | fail → reference dropped, reported |
| Claim support (step 7, agent not script) | stored passage entails the judgement | supported / partial / unsupported |

Output: `verification_report.csv` (ref_id, checks, scores, status). "Review" rows are listed briefly to the clinician; nothing is silently rewritten.

Offline fallback: if the script cannot reach NCBI/Crossref (sandboxed environment), the agent records the raw MCP `get_article_metadata` JSON to `sources/` and the script generates CSL from that file. The same tolerant rules then apply to any model-entered fields.

## Model: Opus 5.5
- Skills keep `model: opus` (the alias already resolves to Opus 5.5) and `effort: max`. Agents change `model: inherit` → `opus`, and get effort frontmatter if agent files support it (verify against the Claude Code docs during implementation).
- Name the version in one place only (the README requirements). Elsewhere say "latest Claude Opus".
- Remove the "think deeply / MOST IMPORTANT" emphasis. At max effort it only makes output longer. Keep the reasons (the DOI anecdote).
- The disclaimer records the configured model (`opus`, effort `max`) alongside the self-reported ID.

## Delivery plan (branch `claude/festive-newton-qgh5bf`)

**Phase 0: now, v2.0.1 (independent of the redesign)**
- Opus 5.5 wording across the 7 files, plus Cowork setup notes in the README.
- Set `evidence-search` to `model: opus`.
- Move the evaluation register into the working folder: `clinical-evidence-register.csv`.
- Make script and asset paths resolve against the skill base directory.
- Fix doc drift: README "three skills", the hard-coded `skill_version`, the boilerplate in the skill CLAUDE.md files.

**Phase 1: deterministic references (v2.1.0)**
- `shared/scripts/fetch_metadata.py` (network probe + direct fetch → CSL-JSON) and `verify_references.py` (tolerant A/B or source comparison).
- `render_citations.py` (keys → Vancouver numbering and reference list).
- Update `ledger_to_exports.py` to read the verified records.
- Reduce agent Step 4 to "run the verifier, act on fail/review rows".
- pytest with fixtures covering diacritics, capitalisation, HTML-tag titles, epub-year and wrong-paper cases.

**Phase 2: protocol-reviewer v3 (v3.0.0, ledger schema 2.0)**
- Protocol map → questions → parallel retrieval → per-statement judgements.
- New `agents/evidence-verifier.md` (second reviewer).
- The verifier also produces `refs_b.yaml` for the dual-transcription check.
- New outputs:
  - `[Protocol]_Evidence_Table.xlsx` + `.csv`: one row per reference, with design, n, population, outcome, direction, certainty, supporting passage and linked statements.
  - Traceability matrix (statement → question → evidence IDs → verdict) as a docx appendix plus `[Protocol]_Traceability.csv`.
- Run manifest, workspace store, topic-match reuse.
- Guideline records with verbatim quote, section and access date.

**Phase 3: research-summary on the same pipeline**
- Topic → questions front-end. It reuses steps 3–9 and a narrative template.
- Move the shared consumer steps into `shared/references/pipeline.md`.

**Phase 4: evals and CI (runs alongside every phase)**
- Synthetic protocol fixtures with planted errors (outdated rituximab dose, obsolete titre target, missing CMV prophylaxis section), golden ledgers and a wrong-topic ledger.
- Assertion-based evals run with skill-creator.
- A GitHub Actions workflow running pytest and a link check.

## Verification
- `pytest` over fetch/verify/validate/export, with tolerant-matching cases proven: same paper with different spelling → pass; different paper → fail.
- A dual-transcription test: A/B fixture files with a planted one-character DOI difference and a diacritic-only author difference → the DOI is flagged, the author passes.
- The evidence-table xlsx/csv loads cleanly in R (`readxl::read_excel`, `readr::read_csv`).
- A live smoke test (where network is available): `verify_references.py` on a fixture of 10 real PMIDs plus 1 corrupted DOI plus 1 retracted paper → the expected pass/fail pattern.
- `render_citations.py` numbers citations in order of first use, every key resolves, and pandoc turns the result into `.docx` with the bundled template.
- An end-to-end eval of protocol-reviewer on the planted-error ABOi fixture: all planted errors flagged as Major/Minor, the verifier downgrades at least one deliberately unsupported claim, and all deliverables plus the manifest and register row are written.
- Grep shows no remaining `Opus 4.7` / `opus-4` strings.
