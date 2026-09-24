# Getting a verified evidence base — consumer procedure

**Audience:** every skill that consumes the clinical-evidence reference ledger (today
`research-summary` and `protocol-reviewer`). This is the one shared procedure; SKILL.md
files point here instead of repeating it.

**Paths.** `${CLAUDE_PLUGIN_ROOT}` is the plugin folder and `${CLAUDE_SKILL_DIR}` the
consuming skill's folder — use the absolute paths the skill's Paths section gives for
them (this file is not filled in automatically). `<workspace>` is the researcher's
working folder. Shell commands run from the workspace, so always use absolute, quoted
paths.

```text
skill (lead) ─┬─ guideline-search ×2–3: by body ─┐
              ├─ evidence-search: questions A     ├─ in parallel → ledger_parts/*.yaml
              ├─ evidence-search: questions B     │
              └─ evidence-search: questions C ────┘
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
- **Absent (or the researcher wants a fresh one): search in parallel.** First load the
  guideline cache — guidelines already read on this machine (skip this if the
  researcher asks for a fresh guideline check):

  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/guideline_cache.py" get \
    "<workspace>/.clinical-evidence/guideline_cache" \
    --out "<workspace>/.clinical-evidence/cache_hits.yaml"
  ```

  The cache lives in the researcher's folder, the only place that persists between
  sessions; give the guideline agents the `cache_hits.yaml` path. Then, in **one message**, so they run concurrently, dispatch:
  - `guideline-search` agents with **all** the questions and — for a protocol review —
    the protocol's concrete doses, thresholds and timings, so they pull the exact
    recommendations. Split the guideline bodies between 2–3 agents so no single agent
    becomes the bottleneck (one agent is enough for a narrow topic), typically:
    1. UK bodies of the core specialty (e.g. BTS, UKKA, NHSBT for transplantation);
    2. UK cross-specialty bodies the topic touches (e.g. NICE, BSH, UKHSA Green Book,
       MHRA/SmPC, BSAC);
    3. international bodies (e.g. KDIGO, TTS, ASFA, ESOT, AST).

    Name each agent's bodies in its dispatch, and give each the cache file path.
    Output:
    `<workspace>/.clinical-evidence/ledger_parts/guidelines<N>.yaml`.
  - one `evidence-search` agent per cluster of related questions (2–4 clusters; one is
    fine for a single narrow question) for the primary literature. Output:
    `<workspace>/.clinical-evidence/ledger_parts/part<N>.yaml`.

  Give every agent the topic and population, its questions (ids and text) and the plugin
  version (from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`). Then merge:

  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/merge_ledgers.py" \
    "<workspace>"/.clinical-evidence/ledger_parts/*.yaml \
    --out "<workspace>/.literature_search_ledger.yaml"
  ```

  Merging de-duplicates papers found by more than one agent and renumbers `ref_id`s — do
  it before verification. If an agent reports a missing connector, explain in plain
  language what needs enabling.

### Ask for guidelines that couldn't be read

Guidelines are the backbone of the review, so don't quietly work around a missing one.
After merging, if `metadata.unretrieved_guidelines` lists any `importance: key`
guideline, ask the researcher **once**, in plain language — for each: organisation,
title, year, the link, and which question it matters for — to download the PDF and
add it to their folder (or attach it in the chat). Mention supporting ones in a line.
Say they can reply "continue without" to go on.

- **Files supplied:** dispatch one `guideline-search` agent with the file paths, the
  questions they bear on and its own output (`ledger_parts/uploaded.yaml`); it reads
  them in full. Merge again (all parts), so the new entries replace the gaps.
- **"Continue without" (or no key gaps):** carry on. The document lists every guideline
  that couldn't be read under "Guidance to check by hand".

Supplied guidelines go into the guideline cache like any other, so each only needs
supplying once per folder.

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
   A PMID that PubMed returns **without a DOI** (common for older papers) is
   `{pmid: "…", doi: null}` — that is a normal result, checked on PMID alone, and never
   `not_found`. Use `not_found: true` only when PubMed says the identifier doesn't
   exist; before recording that for a PMID, confirm it with one
   `get_article_metadata` call, because a `not_found` PMID is excluded from the review.
2. Run:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/verify_references.py" \
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

After verification, store the checked guidelines for the next run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/guideline_cache.py" put \
  "<workspace>/.clinical-evidence/guideline_cache" "<workspace>/.literature_search_ledger.yaml"
```

## 3. Validate

```bash
python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/validate_ledger.py" "<workspace>/.literature_search_ledger.yaml"
```

Exit 0 → proceed (surface warnings only if clinically relevant). Exit 1 → explain the
problem in plain language and offer a fresh search. Exit 2 → treat as missing (step 1).
The validator accepts schema `1.x`; a `2.x` ledger means the plugin needs updating — say
so rather than guessing at its structure.

## 4. Use it

- Read the ledger from disk; don't work from memory of the agents' summaries.
- Guidelines are your benchmarks. Quote a grade (as `grade.display`, written naturally —
  "(BTS Grade 1C)") only when the validator did not flag it as "not found in the quoted
  source text"; otherwise give the recommendation without a grade and say the grade
  could not be confirmed. For `ungraded` recommendations, name the body without a grade
  and keep its own strength wording from `source_quote` — NICE's "offer" (strong) vs
  "consider" (weaker), "must" vs "should". Mention a guideline whose `currency.status` is not `current`
  (e.g. past its review date) where you rely on it. In the methods or disclaimer, say
  how many guidelines were read in this run and how many were reused from an earlier
  check (with the oldest `cached_on` date).
- `references[].key_finding` is the quickest way to map evidence to your sections; open
  the full record when you need detail.
- Cite only entries in `guidelines`, `references` and `preprints`. Never cite anything
  in `excluded_references`, and never add a reference that isn't in the ledger.
- **Reference list:** decide your citation order, then run

  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/format_references.py" \
    "<workspace>/.literature_search_ledger.yaml" --ids 5,2,9
  ```

  and paste its output as the list. Don't retype reference text. The script refuses
  unknown or excluded ids.
- **Word document:** write the Markdown, then convert it without spending tokens:

  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/md_to_docx.py" "<file>.md" "<file>.docx" \
    --reference-doc "${CLAUDE_SKILL_DIR}/assets/reference.docx" --install
  ```

  Exit 3 means no pandoc could be found or installed — only then build the `.docx` with
  the environment's built-in Word-document capability.
- **Zotero exports:**

  ```bash
  python "${CLAUDE_PLUGIN_ROOT}/shared/scripts/ledger_to_exports.py" \
    "<workspace>/.literature_search_ledger.yaml" --prefix "<Name>" --outdir "<workspace>"
  ```

## Missing helpers

If PyYAML is missing, the scripts cannot run: ask the researcher to install it
(`pip install pyyaml`) rather than checking the ledger by eye. Do not cite unverified
references.
