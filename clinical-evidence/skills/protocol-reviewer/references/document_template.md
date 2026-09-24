# Protocol review — document structure

Use this structure for both the `.md` source and the `.docx`. Headings are numbered as
shown. Placeholders are in square brackets.

## Title page

- Title: "Review of [Protocol Title]"
- Subtitle: "Evidence-Based Recommendations for Protocol Update"
- Author line: "Clinical Protocol Review — AI-Assisted Analysis"
- Date: [Month Year]

(In Markdown, put these in YAML front matter — `title`, `subtitle`, `author`, `date` — then
`\newpage`.)

## Page 2: draft callout (verbatim, as a highlighted box / block quote)

> **DRAFT — NOT FOR CLINICAL USE**
>
> This is an AI-generated draft document. It has not been verified by a clinician and must
> not be circulated or used for clinical decision-making until it has been reviewed,
> cross-checked, and approved by a qualified professional.
>
> **To approve this document:** (1) review all recommendations and references, (2) delete
> this callout, (3) complete the "Reviewed and approved by" field in the Transparency
> Disclaimer (section 6).

## Sections

**1. Executive Summary** — 300–500 words: what was reviewed, counts by classification,
the most important changes, guidelines consulted, number of references, overall
assessment.

**2. Methodology** — review date; the review questions agreed with the clinician
(numbered, as in the traceability matrix); sources searched (PubMed, Scholar Gateway,
guideline bodies with editions/dates, plus preprint/trial registries if used); date range
and study types prioritised; how references were verified (independent second reading
cross-checked against the search, with the number excluded); how judgements were checked
(independent second reviewer; numbers challenged, revised and referred to the MDT); the
classification scheme.

**3. Section-by-Section Review** — one subsection per protocol section, in protocol order:

```markdown
## 3.1 [Section title from protocol]

**Current protocol position:** [brief paraphrase]

**National guideline position:** [what guidelines say, grade inline — e.g. "BTS recommends
a target titre ≤1:8 at transplantation (BTS Grade 1C) [4]"]

**Recent evidence:** [synthesis with citations — "A 2024 meta-analysis [7] found…"]

**Assessment:** [Aligned | Minor update | Major update | New addition | Remove]
· Confidence: [high | moderate | low] · [⚠ Patient safety] · [£ Commissioning]

**Recommendation:** [clear and actionable, with its basis — a guideline grade where one
exists ("Update target titre to ≤1:8 IgG (BTS Grade 1C; supported by [4, 7]).");
otherwise the evidence it rests on ("Consider low-dose rituximab (200 mg): observational
data suggest similar outcomes with fewer infections, low certainty [9, 12]." or "Expert
opinion; no guideline or trial addresses this [5].")]
```

The reader sees one reconciled recommendation per item. The second reviewer's comments,
and how each was resolved, stay in the traceability matrix and evidence table; don't add
a "second reviewer" paragraph to the section.

Where the two reviews disagreed and the evidence doesn't settle who is right
(`outcome: mdt_decision`), replace the **Recommendation** line with:

```markdown
**For MDT decision:** [one sentence on why this is uncertain — what the evidence does and
does not show]

- **Option A — [position]:** for — [cited pros]; against — [cited cons]
- **Option B — [position]:** for — [cited pros]; against — [cited cons]

[What would settle it — e.g. local audit data, a pending trial — if known.] The choice
rests with the MDT.
```

Quote only grades confirmed in the guideline's own text (the build refuses others);
ungraded guidance is cited without a grade but keeps the guideline's strength wording
("NICE recommends offering …" vs "… suggests considering …"). Grades read naturally in the prose — "(BTS Grade 1C)", "(KDIGO 2C)" — not field names
such as "grade display:". Keep doses, thresholds and durations specific where a guideline
gives them; "per unit protocol" is only acceptable when no guideline or evidence
specifies a value, and then say so.

**4. Summary of Recommendations** — table, one row per judgement (J-numbers match the
traceability matrix); safety-flagged rows first. For MDT-decision items, the key
recommendation cell reads "MDT decision: [A] vs [B]". Keep cells short and whole — no
truncation marks:

| # | Section | Topic | Assessment | Key recommendation |
|---|---------|-------|------------|--------------------|

**5. Additional Considerations** — topics the protocol omits but current guidelines or
evidence require (e.g. registry reporting, consent, service standards), commissioning or
business-case implications, emerging evidence (preprints labelled as such) and relevant
ongoing trials (NCT number, phase, size, expected completion).

**6. Transparency Disclaimer**

> *This review was produced using AI-assisted evidence synthesis (Claude, Anthropic) with
> PubMed and Scholar Gateway searches. The AI system was used for literature retrieval and
> structured analysis; clinical judgement and final recommendations remain the
> responsibility of the reviewing clinician and the approving MDT. Reference metadata was
> retrieved from PubMed and its identifiers independently checked
> against PubMed before citation.*
>
> **Reviewed and approved by:** ______________________ *(name, title, and institution)*
>
> *AI system metadata: clinical-evidence v[plugin version] · [model identifier] · PubMed MCP
> · Scholar Gateway · Search date [YYYY-MM-DD] · Review date [YYYY-MM-DD] · Verification:
> [metadata.verification] · Second review: [n] judgements challenged, [m] revised, [k] for
> MDT decision ·
> [github.com/Laszlo75/clinical-skills](https://github.com/Laszlo75/clinical-skills)*

**7. References** — numbered in order of first citation, generated by
`format_references.py --ids <ref_ids in citation order>` and inserted as-is. Guidelines
appear in the list like papers. DOIs and URLs are clickable links.

**Appendix A. Traceability Matrix** — the Markdown table produced by `review_tables.py`
(`.clinical-evidence/traceability.md`), inserted as-is: protocol statement → review
question → evidence → assessment → second review. Note under it that the full evidence
table and matrix are provided as `[Protocol_Name]_Evidence_Table.xlsx` / `.csv`.

## Citation style

Numbered, square brackets: `[1]`, `[2, 3]`, `[4–6]` — one bracket per citation point,
numbers ascending, runs collapsed (`[2, 22–25]`, not `[22, 2], [23, 24, 25]`). Every
factual claim cited; every listed reference cited at least once. Attach a guideline
grade only to the recommendation that carries it — never to a statement of what a
guideline does not cover.
