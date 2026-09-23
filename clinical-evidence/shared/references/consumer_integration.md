# Getting a verified evidence base — consumer procedure

**Audience:** every skill that consumes the clinical-evidence reference ledger (today
`research-summary` and `protocol-reviewer`). This is the one shared procedure; SKILL.md
files point here instead of repeating it.

**Paths.** `[skill-path]` is the consuming skill's absolute base directory, so the
scripts live at `[skill-path]/../../shared/scripts/`. `<workspace>` is the researcher's
working folder. Shell commands run from the workspace, so always use absolute, quoted
paths.

```text
evidence-search agent ──writes──▶ <workspace>/.literature_search_ledger.yaml   (hidden)
                                          │
reference-checker agent ──writes──▶ <workspace>/.clinical-evidence/refs_b.yaml (hidden)
                                          │
verify_references.py ── cross-checks A vs B, excludes failures ──▶ validate_ledger.py
                                          │
                        consumer writes its document; format_references.py builds the list
```

The researcher never sees any of this. Don't mention YAML, ledgers or file paths to
them; talk about "the literature search" and "checking the references".

## 1. Find or build the ledger

The ledger lives at exactly `<workspace>/.literature_search_ledger.yaml`.

- **Present:** read `metadata.topic` and `metadata.search_date`, and tell the researcher
  in one line what search you are about to use and how old it is, so they can ask for a
  fresh one. If the topic clearly doesn't match the current task, or the search is old
  for a fast-moving field (roughly > 6 months), offer a fresh search instead.
- **Absent (or the researcher wants a fresh one):** dispatch the `evidence-search` agent
  with the topic, the specific sub-questions you need answered, likely guideline bodies,
  the plugin version (from `[skill-path]/../../.claude-plugin/plugin.json`) and the
  output path. It returns a short summary when the ledger is written. If the agent
  reports a missing connector, explain in plain language what needs enabling.
- **Several questions?** You may dispatch several `evidence-search` agents in parallel,
  each with a cluster of questions and its own output file (e.g.
  `<workspace>/.clinical-evidence/ledger_parts/part1.yaml`), then combine them:

  ```bash
  python "[skill-path]/../../shared/scripts/merge_ledgers.py" \
    "<workspace>"/.clinical-evidence/ledger_parts/*.yaml \
    --out "<workspace>/.literature_search_ledger.yaml"
  ```

  Merge before verification — it renumbers `ref_id`s.

## 2. Verify the references (whenever any reference lacks an `integrity` block)

A reused ledger that was already verified skips this step.

1. Dispatch the `reference-checker` agent with **only** the identifiers — the PMIDs, plus
   DOIs for references without a PMID — and the output path
   `<workspace>/.clinical-evidence/refs_b.yaml`. Don't pass titles, authors or the
   ledger: the second reading has to be independent to be worth anything.
2. Run:

   ```bash
   python "[skill-path]/../../shared/scripts/verify_references.py" \
     "<workspace>/.literature_search_ledger.yaml" \
     --against "<workspace>/.clinical-evidence/refs_b.yaml" --apply
   ```

   The comparison is tolerant: case, diacritics, HTML markup, punctuation and an epub
   vs print year all pass. A different PMID or DOI, a title that belongs to another
   paper, or a retraction **fails**, and the reference moves to `excluded_references` so
   it can never be cited. `review` means the identifiers agree but a descriptive field
   (usually a consortium author name) differs.
3. Tell the researcher briefly: how many references were checked, anything excluded and
   why (in plain words — e.g. "one paper's identifier pointed to a different
   article, so I left it out"), and any `review` items worth a glance. If an excluded
   paper was central to a sub-question, say so, and consider asking the search agent
   for a replacement.

## 3. Validate

```bash
python "[skill-path]/../../shared/scripts/validate_ledger.py" "<workspace>/.literature_search_ledger.yaml"
```

Exit 0 → proceed (surface warnings only if clinically relevant). Exit 1 → explain the
problem in plain language and offer a fresh search. Exit 2 → treat as missing (step 1).
The validator accepts schema `1.x`; a `2.x` ledger means the plugin needs updating — say
so rather than guessing at its structure.

## 4. Use it

- Read the ledger from disk; don't work from memory of the agent's summary.
- Guidelines are your benchmarks. Quote grades using `grade.display` verbatim.
- `references[].key_finding` is the quickest way to map evidence to your sections; open
  the full record when you need detail.
- Cite only entries in `guidelines`, `references` and `preprints`. Never cite anything
  in `excluded_references`, and never add a reference that isn't in the ledger.
- **Reference list:** decide your citation order, then run

  ```bash
  python "[skill-path]/../../shared/scripts/format_references.py" \
    "<workspace>/.literature_search_ledger.yaml" --ids 5,2,9      # add --json for code
  ```

  and use its output for the list — pasted into Markdown, or read as JSON by the code
  that builds the `.docx`. Don't retype reference text. The script refuses unknown or
  excluded ids.
- **Zotero exports:**

  ```bash
  python "[skill-path]/../../shared/scripts/ledger_to_exports.py" \
    "<workspace>/.literature_search_ledger.yaml" --prefix "<Name>" --outdir "<workspace>"
  ```

## Missing helpers

If PyYAML is missing, the scripts cannot run: ask the researcher to install it
(`pip install pyyaml`) rather than checking the ledger by eye. If the `reference-checker`
agent is unavailable, the plugin install is incomplete — say so; do not cite unverified
references.
