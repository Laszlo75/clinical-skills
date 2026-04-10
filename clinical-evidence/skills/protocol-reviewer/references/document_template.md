# Review Document Template — Markdown-First Approach

## Strategy

Write the review content as a **Markdown file** first, then convert to .docx using pandoc
with a styled reference template. This keeps the agent focused on clinical content quality
rather than fighting with docx-js boilerplate.

## Why Markdown First?

- The agent writes natural structured text instead of JavaScript
- Clickable hyperlinks work natively: `[link text](https://...)`
- In-text citations are just `[1]` in plain text
- Tables work in standard markdown
- Pandoc produces clean .docx that opens reliably in Microsoft Word
- The reference template handles fonts, colours, heading styles, and page layout
- Content is easy to review and debug before conversion

## Step-by-Step Process

### 1. Write the review as Markdown

Create a file called `[Protocol_Name]_Review_[Year].md` with this structure:

```markdown
---
title: "Review of [Protocol Title]"
subtitle: "Evidence-Based Recommendations for Protocol Update"
author: "Clinical Protocol Review — AI-Assisted Analysis"
date: "[Month Year]"
---

\newpage

> **DRAFT — NOT FOR CLINICAL USE**
>
> This is an AI-generated draft document. It has not been verified by a clinician
> and must not be circulated or used for clinical decision-making until it has been
> reviewed, cross-checked, and approved by a qualified professional.
>
> **To approve this document:** (1) review all recommendations and references,
> (2) delete this callout, (3) complete the "Reviewed and approved by" field in
> the Transparency Disclaimer (section 6).

# 1. Executive Summary

[300-500 words covering: what was reviewed, key findings by classification,
number of references, guidelines consulted, overall assessment]

# 2. Methodology

[Date of review, databases searched, date range, study types prioritised,
guidelines consulted with edition/dates, classification system used]

# 3. Section-by-Section Review

## 3.1 [Section Title from Protocol]

**Current protocol position:** [Brief paraphrase of what the protocol says]

**National guideline position:** [What guidelines say, with evidence grades.
ALWAYS include the grade — e.g., "BTS recommends target titre <1:8 at
transplantation (Grade 1C)"]

**Recent evidence:** [Summary citing papers as numbered references, e.g.,
"A recent meta-analysis [3] found no difference in outcomes. A UK registry
study confirmed this [7]."]

**Assessment:** Major Update

**Recommendation:** [Clear, actionable recommendation with evidence grade.
e.g., "Update target titre to ≤1:8 IgG (BTS Grade 1C, supported by [3, 7])."]

---

## 3.2 [Next Section Title]

[Repeat the same structure for each protocol section]

---

# 4. Summary of Recommendations

| # | Section | Topic | Assessment | Key Recommendation |
|---|---------|-------|------------|-------------------|
| 1 | 3.1 | Titre targets | Major update | Update to ≤1:8 IgG |
| 2 | 3.2 | Rituximab dose | Major update | Adopt 375 mg/m² |
| ... | ... | ... | ... | ... |

# 5. Additional Considerations

[Topics not in the original protocol but required by current guidelines
or supported by new evidence — e.g., registry reporting, consent requirements,
service delivery standards]

# 6. Transparency Disclaimer

*This review was produced using AI-assisted evidence synthesis (Claude, Anthropic) with PubMed and Scholar Gateway searches. The AI system was used for literature retrieval and structured analysis; clinical judgement and final recommendations remain the responsibility of the reviewing clinician and the approving MDT. References have been verified against PubMed metadata.*

**Reviewed and approved by:** ______________________ *(name, title, and institution)*

*AI system metadata: clinical-evidence v[plugin version] · [model identifier] · PubMed MCP · Scholar Gateway · Review date [YYYY-MM-DD] · [github.com/Laszlo75/clinical-skills](https://github.com/Laszlo75/clinical-skills)*

# 7. References

1. Author AB, Author CD, et al. Title of the article. *Journal Name*.
   Year;Vol(Issue):Pages. PMID: 12345678.
   [DOI](https://doi.org/10.1234/example)

2. British Transplantation Society. Guidelines for Antibody Incompatible
   Transplantation, Third Edition. February 2016.
   [BTS Guidelines](https://bts.org.uk/guidelines-standards/)

3. [Continue numbering sequentially...]
```

### 2. Convert to .docx using pandoc

The skill bundles a `reference.docx` template (in the `assets/` directory) that sets
Arial font, A4 page size, navy headings, headers/footers, and page numbers.

```bash
pandoc "[Protocol_Name]_Review_[Year].md" \
  -o "[Protocol_Name]_Review_[Year].docx" \
  --reference-doc="[skill-path]/assets/reference.docx" \
  --from=markdown+yaml_metadata_block \
  --to=docx
```

The YAML frontmatter (`title`, `subtitle`, `author`, `date`) is rendered as a title
block on the first page by pandoc. The `\newpage` after the frontmatter forces the
executive summary onto page 2, creating a clean title page.

### 3. Also produce the .bib and PMIDs.txt files

After the markdown and docx are done, generate the `.bib` and `PMIDs.txt` files using
the same format as the literature-search skill (see `../literature-search/references/evidence_summary_template.md`
for the BibTeX format). Copy all reference metadata verbatim from the reference ledger
loaded in Step 2.

## Key Content Rules

### Evidence grades — do not skip

Every recommendation backed by a national guideline MUST include the evidence grade
inline. This is what clinicians look for first. Examples:

- "BTS recommends target titre <1:8 at transplantation **(Grade 1C)**"
- "NICE recommends DOACs over warfarin for non-valvular AF **(Strength: Strong)**"
- "KDIGO suggests monitoring DSA quarterly **(Grade 2C)**"

If you don't include the grade, the clinician has to go look it up themselves — which
defeats the purpose of the review.

### In-text citations — every claim needs a source

Use numbered references in square brackets: `[1]`, `[2, 3]`, `[4-6]`.
Every reference in the list must be cited at least once in the body.
Every factual claim in the review must cite its source.

### Clickable links in references — essential

In the markdown, write each reference with its DOI or URL as a clickable link:

```markdown
1. Smith AB, et al. Title. *Journal*. 2024;36:100. PMID: 12345678.
   [DOI](https://doi.org/10.1234/example)
```

Pandoc converts these to clickable hyperlinks in the .docx automatically.
This is one of the most valued features — it saves clinicians time.

### Reference accuracy — copy from the reference ledger, never from memory

Every DOI in the reference list MUST come directly from the reference ledger
produced by the literature-search skill (loaded and validated in Step 2). DOIs
are opaque strings — you cannot reconstruct them from the paper title or journal.

When writing the reference list, work from the parsed ledger in your context.
Copy DOIs, titles, and author lists exactly as they appear. Use `grade.display`
verbatim for any inline evidence grade citation.

### Guidelines in the reference list

National guidelines (BTS, NICE, KDIGO, etc.) must appear as numbered entries
in the reference list, just like PubMed papers. Use the guideline body's URL:

```markdown
15. British Transplantation Society. Guidelines for Antibody Incompatible
    Transplantation, 3rd Edition. 2016.
    [BTS Guidelines](https://bts.org.uk/guidelines-standards/)
```

## Output Files

The skill should produce four files in the user's workspace folder:

1. **`[Protocol_Name]_Review_[Year].md`** — the markdown source (useful for future editing)
2. **`[Protocol_Name]_Review_[Year].docx`** — the converted Word document
3. **`[Protocol_Name]_References.bib`** — BibTeX for Zotero import
4. **`[Protocol_Name]_PMIDs.txt`** — PMID list for bulk Zotero import
