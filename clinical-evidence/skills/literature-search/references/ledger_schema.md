# Reference ledger — internal schema

**Schema version:** `1.0`
**Status:** Stable. First versioned schema.
**Audience:** The `literature-search` skill (producer) and any skill that consumes its evidence (`protocol-reviewer`, future `literature-review`, etc.). **Not** a user-facing document — researchers never see this file or the ledger it describes.

This document is the **single source of truth** for the internal reference ledger format. The ledger is an internal artifact, not one of the skill's user-facing outputs.

---

## What the ledger is (and why it's hidden)

The reference ledger is a YAML file containing every piece of evidence the literature search turned up — guidelines, peer-reviewed references, preprints, ongoing trials. It exists for two reasons:

1. **Quality control for the producer.** The ledger is written incrementally during the search: after every `get_article_metadata` call, the producer appends the returned DOI/PMID/title/author fields to the ledger file *before doing anything else*. This mechanical tool-output → file → file-read cycle is the only reliable defence against DOI hallucination. (The real failure case: in testing, a DOI that differed by three characters from the correct one was produced because the model wrote from memory. The incremental-write-to-file pattern prevents that. It has to keep existing.)

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

1. **`ledger_schema_version`** is set to the schema version the producer targets (currently `"1.0"`).
2. **Every DOI** in `references[]` is copied character-for-character from its authoritative source (PubMed for PubMed references, publisher metadata for Scholar Gateway-only references). DOIs are never reconstructed from memory.
3. **Every PMID** is a real PubMed identifier that the producer retrieved during the search — no fabricated IDs.
4. **Every reference has a verified title, first author, and journal** copied verbatim from the source.
5. **Retracted papers** are excluded. Producers must scan for `[Retracted]` / `[Retraction of:` markers in titles and drop those entries before writing the ledger.
6. **Every guideline recommendation** carries a structured `grade` object (see "Grade object" below) — not a free-text string.
7. **The final ledger passes** `scripts/validate_ledger.py` — if validation fails, the producer must fix the issues before finishing the search.
8. **The ledger is written to the canonical path** `<workspace>/.literature_search_ledger.yaml`.

## Consumer contract

A consumer of this ledger may rely on:

1. **The structure below is stable** within the current schema MAJOR version.
2. **Reference metadata (DOI, PMID, title, authors) is trustworthy** — the producer verified it character-by-character against PubMed. Consumers should not re-fetch.
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

- `preprints` — bioRxiv / medRxiv preprints (from literature-search Step 3b)
- `ongoing_trials` — ClinicalTrials.gov records (from literature-search Step 3b)

---

## Full structure

```yaml
metadata:
  ledger_schema_version: "1.0"        # REQUIRED — semver of this schema
  topic: "CMV prophylaxis in SOT"     # REQUIRED — the clinical topic searched
  search_date: "2026-04-10"           # REQUIRED — ISO 8601 YYYY-MM-DD
  skill_version: "1.0.0"              # REQUIRED — producer version (since clinical-evidence v1.0.0, this is the plugin version)
  model_id: "claude-opus-4-6"         # REQUIRED — model identifier used
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
    pmid: "31107464"                  # REQUIRED — PubMed ID, or null for Scholar Gateway-only
    doi: "10.1111/ajt.15493"          # REQUIRED — copied verbatim from source
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

## Validation

Every producer and consumer must run `literature-search/scripts/validate_ledger.py` against the ledger:

```bash
python scripts/validate_ledger.py /path/to/.literature_search_ledger.yaml
```

Exit codes:
- `0` — ledger is valid (may still print `WARN:` lines; warnings are non-blocking).
- `1` — ledger has one or more `ERROR:` issues. Do not proceed.
- `2` — ledger file missing or cannot be parsed as YAML.

Prose validation in SKILL.md files should defer to this script — a consumer's ledger-loading step becomes "run the validator; if it exits non-zero, stop and show the user the errors."

---

## Change log

### 1.0 (2026-04-10)
- First versioned schema. Introduced `ledger_schema_version` field in `metadata`.
- Evidence grades are structured objects (`system`, `code`, `display`) — clean break from free-text.
- Ledger moved to hidden canonical path `<workspace>/.literature_search_ledger.yaml`; no longer listed in user-facing outputs.
- Added companion validator at `scripts/validate_ledger.py`.
- Legacy (pre-1.0) ledgers are not compatible and must be regenerated.
