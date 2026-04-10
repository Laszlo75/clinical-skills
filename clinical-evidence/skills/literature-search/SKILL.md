---
name: literature-search
model: opus
effort: max
description: >
  Search PubMed, Scholar Gateway, and national guideline websites for clinical evidence
  on a given topic, then produce a verified reference ledger plus BibTeX and PMID list
  files for Zotero import. Use when the user asks for a literature search, evidence
  review, reference list, or wants to find what the latest evidence says about a
  clinical topic. Also triggers when the user mentions a clinical topic casually and
  asks what the latest evidence or guidelines say — even without using the words
  "literature search" (e.g., "I'm updating our CMV protocol, what's the current
  thinking?", "what does NICE say about X?"). Triggers include: "literature search",
  "search PubMed", "find evidence on", "what does the latest evidence say about",
  "evidence review", "reference list for", "search the literature", "what do the
  guidelines say about", or any request for clinical evidence on a specific topic.
---

# Clinical Literature Search

You are the user-facing trigger for a clinical literature search. Your job is to parse
and confirm the topic with the researcher, dispatch the `evidence-search` agent to do
the actual PubMed / Scholar Gateway / guideline search in isolated context, validate the
ledger the agent produces, and write two Zotero-friendly export files from it. You then
point the researcher at the right downstream skill (`research-summary` for a narrative
document, `protocol-reviewer` for protocol review).

## Quick Start

**Input:** A clinical topic (free text).
**Output:** 2 user-facing files — BibTeX (`.bib`) and PMID list (`.txt`). A hidden
reference ledger (`.literature_search_ledger.yaml`) is also written to the workspace for
downstream consumer skills; the researcher never needs to open it.
**Happy path:** Parse topic → confirm scope with researcher → dispatch `evidence-search`
agent → validate returned ledger → write `.bib` + PMIDs → point at next skill.

## Why this is thin

The heavy lifting (PubMed MCP calls, Scholar Gateway passages, full-text retrievals,
reference verification) runs inside the `evidence-search` agent so tool-output traffic
does not pollute the main conversation. The agent writes the canonical hidden ledger.
This skill exists because Claude Code agents cannot be invoked directly by a user — the
skill is the user-facing trigger phrase that dispatches the agent.

## Prerequisites

The ledger contract is defined once in
[`references/ledger_schema.md`](references/ledger_schema.md). The executable validator
at [`scripts/validate_ledger.py`](scripts/validate_ledger.py) is the real enforcer. Do
not re-implement ledger validation by eye.

## High-level workflow

```text
1. PARSE + CONFIRM topic    ──►   2. DISPATCH evidence-search agent
        │                                    │
        ▼                                    ▼
3. VALIDATE returned ledger      ──►   4. WRITE .bib + PMIDs
        │
        ▼
5. POINT researcher at next skill
```

Follow each step carefully.

---

## Step 1: Parse and confirm the topic

From the researcher's free-text request, derive:

1. **Clinical topic summary** — a concise statement of what evidence is being sought.
2. **Primary MeSH terms / keywords** for PubMed searches.
3. **Relevant UK guideline bodies** — BTS, NICE, SIGN, BSH, BSAC, RCPath, UKKA, NHSBT,
   BOA, or other specialty bodies as appropriate.
4. **International guidelines** if relevant — KDIGO, ISHLT, ESOT, EAU, AST, etc.

Summarise your search plan back to the researcher in 3–4 sentences so they can correct
any misinterpretation or add missing subtopics **before** the expensive agent dispatch.

### Scope check

- **Too broad** (maps to >5 distinct subtopics or very general MeSH terms like
  "neoplasms"): ask the researcher to narrow. A search on "cancer treatment" will
  produce an unfocused ledger — "immunotherapy for advanced NSCLC" is actionable.
- **Too narrow** (only 2–3 papers likely exist): warn the researcher that results may
  be limited. Consider broadening the date range or widening the inclusion criteria.

Do not proceed to Step 2 until the researcher has confirmed the scope.

## Step 2: Dispatch the evidence-search agent

Tell the researcher: *"I'll now search PubMed, Scholar Gateway, and the relevant
guideline bodies for evidence on [topic]. This may take several minutes and runs in an
isolated context to keep the main conversation clean."*

Use the **Agent tool** with `subagent_type: "evidence-search"`. Your prompt to the agent
must include:

- The **confirmed clinical topic** (from Step 1).
- The **MeSH terms / keywords** derived in Step 1.
- The **list of guideline bodies** to prioritise.
- The **plugin version** read from `../../.claude-plugin/plugin.json` (so the agent can
  populate `metadata.skill_version` correctly).
- An explicit instruction: *"Write the verified ledger to
  `<workspace>/.literature_search_ledger.yaml` and return the short structured summary
  described in your system prompt."*

The agent will do the full search (guidelines, PubMed, Scholar Gateway, optional
preprints and trials), build the ledger incrementally as it goes, verify every reference
character-by-character against PubMed, and return a short structured summary. Wait for
it to complete.

### If the agent fails

If the agent reports a failure (e.g., PubMed MCP unavailable), translate the error into
plain language for the researcher and offer to re-dispatch once the underlying issue is
resolved. Do not try to run the search inline yourself — the whole point of the agent
is to keep tool output out of the main context.

## Step 3: Validate the returned ledger

Once the agent returns, run the bundled validator against the canonical path. This is a
non-negotiable gate:

```bash
python scripts/validate_ledger.py <workspace>/.literature_search_ledger.yaml
```

- **Exit 0** — ledger is valid. Proceed to Step 4. Any `WARN:` lines are informational;
  surface them only if clinically relevant (e.g., very few references).
- **Exit 1** — show the `ERROR:` lines to the researcher in plain language (translate
  them — don't dump raw script output). Offer to re-dispatch the agent, which will
  overwrite the bad ledger.
- **Exit 2** — the ledger file is missing or cannot be parsed. Re-dispatch the agent.

The validator is the executable counterpart to `references/ledger_schema.md`. If the
two ever disagree, the validator wins.

## Step 4: Write the Zotero export files

Re-read `.literature_search_ledger.yaml` from disk — do **not** rely on memory of the
agent's summary. From the ledger, generate exactly two user-facing files in the
researcher's workspace:

### 4a. `[Topic_Name]_References.bib`

One BibTeX entry per reference. Use the `references[]` array from the ledger. Copy
PMID, DOI, first author, full author list, title, journal, year, volume, and pages
verbatim — do not reformat or reconstruct any field. Use the format:

```bibtex
@article{pmid12345678,
  author  = {Kotton CN and Kumar D and Caliendo AM and others},
  title   = {The Third International Consensus Guidelines on...},
  journal = {Transplantation},
  year    = {2018},
  volume  = {102},
  pages   = {900-931},
  pmid    = {31107464},
  doi     = {10.1111/ajt.15493}
}
```

### 4b. `[Topic_Name]_PMIDs.txt`

One PMID per line, for Zotero bulk import. Include only references with a non-null
`pmid` field — Scholar Gateway-only references without a PMID are omitted from this
file. The `.bib` file still contains them (by DOI).

### What not to produce

This skill **does not** produce:

- A `.md` or `.docx` narrative document. The narrative evidence summary is the job of
  the `research-summary` consumer skill.
- A protocol review document. That is the job of the `protocol-reviewer` consumer
  skill.
- Any duplicate or alternative version of the ledger itself.

## Step 5: Point the researcher at the next skill

End the session by telling the researcher what was produced and what to do next:

> *Evidence ledger + reference exports are ready for [topic]. N peer-reviewed references
> and M guidelines are in the ledger. You can now:*
>
> - *run `research-summary` to produce a narrative evidence summary document (`.md` +
>   `.docx`), or*
> - *run `protocol-reviewer` to review a clinical protocol against this evidence.*
>
> *Both skills will pick up the ledger automatically — you don't need to point them at
> a file.*

**Do not** mention the YAML ledger filename or the hidden path in the final message.
The researcher's mental model is: *"I asked for a literature search, I got reference
export files, and the next skill will know what to do."*

---

## Tool dependencies

Required:

- **Python 3 + PyYAML** — used by the ledger validator in Step 3.
- **evidence-search agent** — ships in the same `clinical-evidence` plugin at
  `../../agents/evidence-search.md`. The agent in turn requires:
  - **PubMed MCP** (`search_articles`, `get_article_metadata`, `get_full_text_article`,
    `find_related_articles`)
  - **Scholar Gateway** (`semanticSearch`)
  - **WebSearch / WebFetch** — for national guideline pages

Optional (enhance agent coverage when available):

- **bioRxiv MCP** (`search_preprints`, `search_published_preprints`)
- **Clinical Trials MCP** (`search_trials`, `get_trial_details`, `analyze_endpoints`)

### Handling missing tools

- **PyYAML not installed:** the validator cannot run. Tell the researcher: *"I can't
  verify the evidence base I just generated — a small helper is missing. Please run
  `pip install pyyaml` and try again."*
- **evidence-search agent not installed:** this should never happen with a normal
  `clinical-evidence` plugin install (they ship together). If the Agent tool reports
  the subagent type is unknown, tell the researcher the plugin is incomplete and needs
  to be reinstalled.
- **PubMed MCP unavailable (agent reports failure):** tell the researcher PubMed MCP
  is required and link them to the setup instructions. Do not attempt an inline
  fallback — the reference integrity workflow depends on PubMed metadata.
