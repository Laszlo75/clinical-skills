# Getting a verified evidence base — consumer procedure

**Audience:** every skill that consumes the clinical-evidence reference ledger (today
`research-summary` and `protocol-reviewer`). This is the one shared procedure; SKILL.md
files point here instead of repeating it.

**Paths.** `[skill-path]` is the consuming skill's absolute base directory, so the
scripts live at `[skill-path]/../../shared/scripts/`. `<workspace>` is the researcher's
working folder. Shell commands run from the workspace, so always use absolute, quoted
paths.

```text
skill (lead) ─┬─ evidence-search: questions A ─┐
              ├─ evidence-search: questions B  ├─ in parallel → ledger_parts/*.yaml
              └─ evidence-search: questions C ─┘
merge_ledgers.py → .literature_search_ledger.yaml (hidden)
PubMed ID conversion (skill) → refs_b.yaml → verify_references.py → validate_ledger.py
skill writes its document; format_references.py builds the reference list
```

The researcher never sees any of this. Don't mention YAML, ledgers or file paths to
them; talk about "the literature search" and "checking the references".

**Speed and cost.** Every tool result read in the main conversation is carried through
the rest of the run, so keep bulky material (abstracts, full texts, guideline pages) in
the search agents and bring back only their short summaries.

## 1. Find or build the ledger

The ledger lives at exactly `<workspace>/.literature_search_ledger.yaml`.

- **Present:** read `metadata.topic` and `metadata.search_date`, and tell the researcher
  in one line what search you are about to use and how old it is, so they can ask for a
  fresh one. If the topic clearly doesn't match the current task, or the search is old
  for a fast-moving field (roughly > 6 months), offer a fresh search instead.
- **Absent (or the researcher wants a fresh one): search in parallel.** Split the
  questions into 2–4 clusters of related questions (one cluster is fine for a single
  narrow question) and dispatch one `evidence-search` agent per cluster **in the same
  message**, so they run concurrently. Give each: its questions (ids and text), the
  topic and population, likely guideline bodies, the plugin version (from
  `[skill-path]/../../.claude-plugin/plugin.json`) and its own output file,
  `<workspace>/.clinical-evidence/ledger_parts/part<N>.yaml`. Then merge:

  ```bash
  python "[skill-path]/../../shared/scripts/merge_ledgers.py" \
    "<workspace>"/.clinical-evidence/ledger_parts/*.yaml \
    --out "<workspace>/.literature_search_ledger.yaml"
  ```

  Merging de-duplicates papers found by more than one agent and renumbers `ref_id`s — do
  it before verification. If an agent reports a missing connector, explain in plain
  language what needs enabling.

## 2. Verify the references (whenever any reference lacks an `integrity` block)

A reused ledger that was already verified skips this step.

The failure that matters is a real identifier attached to the wrong paper — a PMID and a
DOI that belong to different articles. An independent reading of the identifier pairs
catches it cheaply:

1. List the ledger's PMIDs (and DOIs for references without a PMID). Call PubMed
   `convert_article_ids` yourself — PMIDs in one call (up to 200 per call), DOIs in
   another with `id_type: doi` — and write each returned pair straight from the tool
   output to `<workspace>/.clinical-evidence/refs_b.yaml`:

   ```yaml
   - {pmid: "29596116", doi: "10.1097/TP.0000000000002191"}
   - {pmid: "30000009", not_found: true}        # PMID PubMed does not recognise
   - {pmid: null, doi: "10.9999/sg.only.2022.8", not_found: true}   # DOI not in PubMed
   ```

   Use only the conversion output — not the ledger — so the check stays independent.
2. Run:

   ```bash
   python "[skill-path]/../../shared/scripts/verify_references.py" \
     "<workspace>/.literature_search_ledger.yaml" \
     --against "<workspace>/.clinical-evidence/refs_b.yaml" --apply
   ```

   A PMID that PubMed doesn't know, or a PMID/DOI pair that doesn't match, **fails**, and
   the reference moves to `excluded_references` so it can never be cited. Case and
   `https://doi.org/` prefixes are tolerated. `review` means PubMed has no DOI for that
   PMID (common for older papers) or a DOI-only paper isn't in PubMed.
3. Tell the researcher briefly: how many references were checked, anything excluded and
   why (in plain words — e.g. "one paper's identifier pointed to a different article, so
   I left it out"). If an excluded paper was central to a question, say so.

(`verify_references.py` also accepts a fuller second reading with titles, authors and
years, compared tolerantly — useful for audits, not needed for routine runs.)

## 3. Validate

```bash
python "[skill-path]/../../shared/scripts/validate_ledger.py" "<workspace>/.literature_search_ledger.yaml"
```

Exit 0 → proceed (surface warnings only if clinically relevant). Exit 1 → explain the
problem in plain language and offer a fresh search. Exit 2 → treat as missing (step 1).
The validator accepts schema `1.x`; a `2.x` ledger means the plugin needs updating — say
so rather than guessing at its structure.

## 4. Use it

- Read the ledger from disk; don't work from memory of the agents' summaries.
- Guidelines are your benchmarks. Quote grades using `grade.display` verbatim.
- `references[].key_finding` is the quickest way to map evidence to your sections; open
  the full record when you need detail.
- Cite only entries in `guidelines`, `references` and `preprints`. Never cite anything
  in `excluded_references`, and never add a reference that isn't in the ledger.
- **Reference list:** decide your citation order, then run

  ```bash
  python "[skill-path]/../../shared/scripts/format_references.py" \
    "<workspace>/.literature_search_ledger.yaml" --ids 5,2,9
  ```

  and paste its output as the list. Don't retype reference text. The script refuses
  unknown or excluded ids.
- **Word document:** write the Markdown, then convert it without spending tokens:

  ```bash
  python "[skill-path]/../../shared/scripts/md_to_docx.py" "<file>.md" "<file>.docx" \
    --reference-doc "[skill-path]/assets/reference.docx" --install
  ```

  Exit 3 means no pandoc could be found or installed — only then build the `.docx` with
  the environment's built-in Word-document capability.
- **Zotero exports:**

  ```bash
  python "[skill-path]/../../shared/scripts/ledger_to_exports.py" \
    "<workspace>/.literature_search_ledger.yaml" --prefix "<Name>" --outdir "<workspace>"
  ```

## Missing helpers

If PyYAML is missing, the scripts cannot run: ask the researcher to install it
(`pip install pyyaml`) rather than checking the ledger by eye. Do not cite unverified
references.
