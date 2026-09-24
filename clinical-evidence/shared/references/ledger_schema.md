# Reference ledger — internal schema

**Schema version:** `1.2`
**Status:** Stable. 1.1 added optional verification fields, 1.2 optional question and appraisal fields; 1.0 and 1.1 ledgers remain valid.
**Audience:** The `evidence-search` agent (producer) and any skill that consumes its evidence (`research-summary`, `protocol-reviewer`, future consumers). **Not** a user-facing document — researchers never see this file or the ledger it describes.

This document is the **single source of truth** for the internal reference ledger format. The ledger is an internal artifact, not one of the consumers' user-facing outputs.

---

## What the ledger is (and why it's hidden)

The reference ledger is a YAML file containing every piece of evidence the literature search turned up — guidelines, peer-reviewed references, preprints, ongoing trials. It exists for two reasons:

1. **Quality control.** The producer copies DOI/PMID/title/author fields into the ledger straight from each `get_article_metadata` response, never from memory. (The real failure case: in testing, a DOI three characters off the correct one was produced from memory. This schema's own early examples paired the Kotton 2018 CMV guideline with a PMID and DOI belonging to other papers — exactly the error independent verification now catches.) Since 1.1, every reference's identifiers are then checked independently against PubMed (the consuming skill's ID-conversion call, compared by `verify_references.py`) before it can be cited.

2. **Handoff between skills.** When a downstream skill (protocol-reviewer, literature-review) needs to cross-reference or summarise the evidence, it reads the ledger instead of re-doing the search. This is faster than re-searching and guarantees the two skills are working from the same verified source.

**Why hidden:** a clinical researcher should not need to know that a YAML file exists, or think about inter-skill handoff, or pick which file to give to the next skill. The researcher experience is: *"search the evidence on X"* → Word document appears; *"review this protocol"* → review document appears. The ledger enables the second step but is invisible during both. Exposing it in the user-facing output list creates cognitive load for zero benefit — researchers don't edit YAML.

---

## Canonical path

The ledger is always written to exactly one location in the user's workspace:

```
<workspace>/.literature_search_ledger.yaml
```

- **Hidden file** (leading dot) so it does not clutter the researcher's folder view.
- **Fixed filename** so any consumer can find it deterministically — no pointer file, no "latest search" logic, no asking the user which YAML to use.
- **Overwritten** on every new search in the same workspace. This is intentional: the latest search is almost always what a downstream skill wants. Researchers who need parallel topics use parallel workspaces.

If a consumer looks for the ledger and it is not present, the consumer's fallback is to auto-trigger a fresh literature search — not to ask the user where a file lives.

---

## Semver policy for this schema

The schema is versioned independently of the `clinical-evidence` plugin. Use the `ledger_schema_version` field in `metadata` — not `skill_version` — to decide compatibility.

- **MAJOR** (e.g., `1.0` → `2.0`) — breaking change. A field was removed or its type changed. Consumers must update before accepting the new ledger.
- **MINOR** (e.g., `1.0` → `1.1`) — additive change. New optional fields. Consumers on `1.x` keep working without modification.
- **PATCH** (e.g., `1.0` → `1.0.1`) — prose/clarification only. No structural change.

A consumer on schema `1.x` must:
- **Accept** any `1.x` ledger.
- **Warn clearly and stop** on `2.x` or higher — the consumer was not written for that schema.
- **Error** on a missing or unparseable `ledger_schema_version` (legacy unversioned ledger — producer must re-run).

---

## Producer contract

A producer of this ledger must guarantee:

1. **`ledger_schema_version`** is set to the schema version the producer targets (currently `"1.1"`).
2. **Every DOI, PMID, title, author list and journal** in `references[]` is copied from its source tool output (PubMed, or Scholar Gateway for papers not in PubMed) — never reconstructed from memory.
3. **Retracted papers** are excluded.
4. **Every guideline recommendation** carries a structured `grade` object (see "Grade object" below) — not a free-text string.
5. **The final ledger passes** `shared/scripts/validate_ledger.py` — if validation fails, the producer must fix the issues before finishing the search.
6. **The ledger is written to the canonical path** `<workspace>/.literature_search_ledger.yaml`.

## Consumer contract

A consumer of this ledger may rely on:

1. **The structure below is stable** within the current schema MAJOR version.
2. **Reference metadata is trustworthy once verified** — a reference carrying an `integrity` block has been independently checked against PubMed (tolerantly: formatting differences pass, a different identifier or paper fails). A ledger with any reference lacking `integrity` must be verified first (see `consumer_integration.md`). Failed references live in `excluded_references` and must never be cited.
3. **Evidence grades are queryable** as structured objects with `system`, `code`, `display` — safe to filter, aggregate, or sort on.
4. **`metadata.search_date`** reliably indicates how fresh the evidence is.
5. **Running `scripts/validate_ledger.py`** on the ledger path is sufficient validation — the consumer does not need to re-implement checks in prose.

---

## Required top-level sections

The YAML must contain these three sections:

- `metadata` — provenance and schema version
- `guidelines` — national and international guideline recommendations
- `references` — peer-reviewed literature

Two sections are optional and may be omitted if empty:

- `preprints` — bioRxiv / medRxiv preprints (from the `evidence-search` agent's Step 3b)
- `ongoing_trials` — ClinicalTrials.gov records (from the `evidence-search` agent's Step 3b)

---

## Full structure

```yaml
metadata:
  ledger_schema_version: "1.2"        # REQUIRED — semver of this schema
  topic: "CMV prophylaxis in SOT"     # REQUIRED — the clinical topic searched
  search_date: "2026-04-10"           # REQUIRED — ISO 8601 YYYY-MM-DD
  skill_version: "1.0.0"              # REQUIRED — producer version (since clinical-evidence v1.0.0, this is the plugin version)
  model_id: "<session model id> (configured: opus)"  # REQUIRED — self-reported ID + configured tier
  mesh_terms:                         # REQUIRED — MeSH terms / keywords used
    - "Cytomegalovirus Infections"
    - "Organ Transplantation"
  guideline_bodies:                   # REQUIRED — bodies consulted
    - "BTS"
    - "KDIGO"
    - "AST"

guidelines:
  - ref_id: 1                         # REQUIRED — sequential integer, unique across guidelines + references
    type: guideline                   # REQUIRED — literal string "guideline"
    title: "KDIGO Clinical Practice Guideline for the Prevention, Diagnosis, Evaluation, and Treatment of CMV in SOT, 2018"
    organisation: "KDIGO"             # REQUIRED — short body name
    year: 2018                        # REQUIRED — integer publication year
    url: "https://kdigo.org/..."      # REQUIRED — authoritative URL
    key_recommendations:              # REQUIRED — list, may be empty
      - text: "Valganciclovir 900 mg daily for 200 days post-transplant in D+/R- recipients"
        grade:                        # REQUIRED — structured grade object
          system: "KDIGO"             # REQUIRED — the grading system used
          code: "1B"                  # REQUIRED — short code
          display: "KDIGO Grade 1B"   # REQUIRED — human-readable form for inline citation

references:
  - ref_id: 2                         # REQUIRED — unique across guidelines + references
    pmid: "29596116"                  # REQUIRED — PubMed ID, or null for Scholar Gateway-only
    doi: "10.1097/TP.0000000000002191"          # REQUIRED — copied verbatim from source
    first_author: "Kotton CN"         # REQUIRED — surname + initials, from PubMed
    authors_full: "Kotton CN, Kumar D, Caliendo AM, et al."  # REQUIRED — full list as PubMed returns it
    title: "The Third International Consensus Guidelines on the Management of Cytomegalovirus in Solid-organ Transplantation"
    journal: "Transplantation"        # REQUIRED
    year: 2018                        # REQUIRED — integer
    volume: "102"                     # REQUIRED — may be empty string if n/a
    pages: "900-931"                  # REQUIRED — may be empty string if n/a
    key_finding: "Preemptive therapy and universal prophylaxis both viable; choice depends on donor/recipient serostatus."
    source: "pubmed"                  # REQUIRED — one of: pubmed | scholar_gateway | both
    full_text_reviewed: true          # REQUIRED — boolean

# Optional — include only if preprints were found
preprints:
  - ref_id: 20
    doi: "10.1101/2025.08.12.12345"
    authors: "Smith J, Jones K, et al."
    title: "Letermovir vs valganciclovir for CMV prophylaxis: a retrospective cohort"
    server: "medrxiv"                 # REQUIRED — one of: medrxiv | biorxiv
    year: 2025
    key_finding: "Letermovir associated with lower late-onset CMV disease at 12 months."
    published_version_doi: null       # REQUIRED — DOI of peer-reviewed version or null

# Optional — include only if relevant trials were found
ongoing_trials:
  - nct_id: "NCT04123456"             # REQUIRED — NCT identifier
    title: "Phase III Letermovir vs Valganciclovir in Kidney Transplant"
    phase: "Phase III"                # REQUIRED — Phase I | Phase II | Phase III | Phase IV
    status: "RECRUITING"              # REQUIRED — RECRUITING | ACTIVE_NOT_RECRUITING | COMPLETED
    estimated_completion: "2027-06"   # REQUIRED — YYYY-MM
    sample_size: 400                  # REQUIRED — integer
    relevance: "Head-to-head comparison in the exact population the protocol covers."
```

---

## The grade object (important — v1.0 change vs unversioned legacy)

Every `key_recommendations[].grade` **must** be a YAML mapping with three string fields:

```yaml
grade:
  system: "BTS"              # Grading system: BTS | NICE | KDIGO | SIGN | GRADE | AST | ISHLT | ...
  code: "1C"                 # Short code as the grading system defines it: 1A, 1B, 1C, 2A, Strong, Moderate, Low, ...
  display: "BTS Grade 1C"    # Full human-readable string suitable for inline citation in a review document
```

**Why structured, not free-text:** downstream consumers need to be able to filter ("show me all Grade 1A recommendations") and aggregate ("three high-strength recommendations support this dose"). A free-text field cannot do that reliably.

**Why `display` as well as `system` + `code`:** consumers that write the grade inline in a review document need one canonical human-readable string. Building it from `system` + `code` in each consumer invites inconsistency ("BTS 1C" vs "BTS Grade 1C" vs "Grade 1C (BTS)"). The producer chooses the canonical form once.

**Legacy ledgers** (produced before schema `1.0`) used a free-text string at this position. These are not compatible — the validator will reject them and the user will be told to re-run the search.

---

## Verification fields (schema 1.1, written by `verify_references.py --apply`)

```yaml
metadata:
  verification: "independent second reading, cross-checked 2026-09-23"   # optional

references:
  - ref_id: 2
    # … fields as above …
    integrity:                        # optional in 1.1; present once verified
      status: "pass"                  # pass | review  ("review" = identifiers agree, a descriptive field needs a human glance)
      checked_on: "2026-09-23"
      notes: ""                       # e.g. "first author differs (KDIGO Work Group vs …)"

excluded_references:                  # optional; references that failed verification
  - ref_id: 4
    pmid: "30000004"
    doi: "10.1016/…"
    title: "…"
    reason: "title similarity 0.21 — likely a different paper"
```

Producers never write these fields. The validator warns when a 1.1 ledger has a reference without `integrity`, and errors if an excluded `ref_id` is still present in `references`.

## Question and appraisal fields (schema 1.2, all optional)

Written by the producer when the dispatching skill supplies review questions (protocol
review always does):

```yaml
metadata:
  questions:                          # the review questions agreed with the clinician
    - {id: Q1, text: "What rituximab dose is recommended for ABOi desensitisation?"}

guidelines:
  - # … as above …
    questions: [Q1]                   # question ids this guideline informs
    key_recommendations:
      - text: "…"
        grade: {system: "BTS", code: "1C", display: "BTS Grade 1C"}
        source_quote: "…verbatim text as published…"   # lets a reviewer check doses at source
        section: "4.2 Desensitisation"
        accessed: "2026-09-23"

references:
  - # … as above …
    questions: [Q1, Q3]
    study_design: "Systematic review and meta-analysis"
    population: "Adult ABOi kidney transplant recipients"
    sample_size: 1426                 # integer, or null
    certainty: "moderate"             # high | moderate | low | very low (GRADE-style)
```

Parallel searches each write a partial ledger; `shared/scripts/merge_ledgers.py` combines
them (de-duplicating on PMID/DOI, unioning `questions`, renumbering `ref_id`s) before
verification.

## Guideline currency and grade provenance (schema 1.3, all optional)

Written by the `guideline-search` agent, which reads the guideline documents themselves:

```yaml
guidelines:
  - # … as above …
    edition: "Third edition"
    pmid: null                        # only when the guideline is a journal publication
    doi: null
    currency:
      status: "past_review_date"      # current | past_review_date | superseded | withdrawn | draft | unknown
      checked_on: "2026-09-24"
      note: "Review date 2019; no newer edition found"
    key_recommendations:
      - text: "…"
        grade:
          system: "BTS"
          code: "1C"                  # exactly as the guideline prints it; "ungraded" if it gives none
          display: "BTS Grade 1C"
          quote: "Grade 1C"           # optional: verbatim text where the grade is printed, if not in source_quote
        source_quote: "…verbatim recommendation text, with the grade where printed with it…"
```

**Reuse from the guideline cache.** A guideline taken unread from the plugin's guideline
cache (`shared/scripts/guideline_cache.py`) carries `cached_on: "YYYY-MM-DD"`, the date
its document was last read. No `cached_on` means the agent read it in this run.

**Grade provenance.** A grade counts as confirmed only if its `code` appears, as a whole
token, in `source_quote` or `grade.quote` (`refmatch.grade_in_source`). The validator
warns about every unconfirmed grade; consumers don't quote those, and `review_tables.py`
refuses (for 1.3 ledgers) a judgement whose grade isn't a confirmed grade of a guideline it
cites. This catches grades supplied from memory — the commonest way a plausible but wrong
grade reaches a document. It does not prove the quote itself is genuine; that is why the
agent reads the source document and the second reviewer re-checks grades on
practice-changing items.

## Validation

Every producer and consumer must run `shared/scripts/validate_ledger.py` against the ledger:

```bash
python shared/scripts/validate_ledger.py /path/to/.literature_search_ledger.yaml
```

Exit codes:
- `0` — ledger is valid (may still print `WARN:` lines; warnings are non-blocking).
- `1` — ledger has one or more `ERROR:` issues. Do not proceed.
- `2` — ledger file missing or cannot be parsed as YAML.

Prose validation in SKILL.md files should defer to this script — a consumer's ledger-loading step becomes "run the validator; if it exits non-zero, stop and show the user the errors."

---

## Change log

### 1.3 (2026-09-24)
- Optional `edition`, `currency`, `pmid`, `doi`, `cached_on` on guidelines; optional `grade.quote`; `code: ungraded` for recommendations a guideline doesn't grade.
- Validator warns when a grade code is not found in the quoted source text, and when a guideline is not current.
- Backward compatible: 1.0–1.2 ledgers validate unchanged.

### 1.2 (2026-09-23)
- Optional `metadata.questions`; `questions`, `study_design`, `population`, `sample_size`, `certainty` on references; `questions` on guidelines; `source_quote`, `section`, `accessed` on guideline recommendations.
- Backward compatible: 1.0 and 1.1 ledgers validate unchanged.

### 1.1 (2026-09-23)
- Added optional `integrity` block per reference, top-level `excluded_references`, and `metadata.verification` — written by the independent verification step, never by the producer.
- `ref_id` uniqueness now also covers `preprints`; duplicate-DOI detection is case-insensitive.
- Fixed the worked example: Kotton et al. 2018 is PMID 29596116, doi:10.1097/TP.0000000000002191.
- Fully backward compatible: 1.0 ledgers validate unchanged.

### 1.0 (2026-04-10)
- First versioned schema. Introduced `ledger_schema_version` field in `metadata`.
- Evidence grades are structured objects (`system`, `code`, `display`) — clean break from free-text.
- Ledger moved to hidden canonical path `<workspace>/.literature_search_ledger.yaml`; no longer listed in user-facing outputs.
- Added companion validator at `scripts/validate_ledger.py`.
- Legacy (pre-1.0) ledgers are not compatible and must be regenerated.
