# Clinical Skills

A Claude Code plugin marketplace hosting AI-assisted tools for clinical evidence synthesis and protocol review. Designed for the UK NHS context and shipped with ISO 42001 transparency disclaimers baked into every output.

## Plugins

| Plugin | Purpose |
|--------|---------|
| [`clinical-evidence`](./clinical-evidence/) | Systematic literature search + clinical protocol review. Bundles two co-designed skills that share a verified reference ledger. |

More clinical plugins may land here over time (audit tooling, a narrative literature-review skill, etc.). Each plugin in this marketplace is scoped to clinical use and is safe to install independently of the others.

## Installation

In Claude Code:

```text
/plugin marketplace add Laszlo75/clinical-skills
/plugin install clinical-evidence
```

Or add the marketplace by URL:

```text
/plugin marketplace add https://github.com/Laszlo75/clinical-skills
```

## Requirements

Each plugin documents its own dependencies. At minimum you will need:

- [Claude Desktop](https://claude.ai/download) or another Claude client with MCP connector support
- Recommended model: **Claude Opus 4.6** — the clinical reasoning, evidence appraisal, and reference integrity checks benefit from stronger model capability
- **pandoc** — markdown to `.docx` conversion (`brew install pandoc` on macOS, `sudo apt install pandoc` on Linux)
- **Python 3 + PyYAML** — used by the reference-ledger validator

## AI Use & Governance (ISO 42001)

Every skill in this marketplace is AI-assisted and produces **draft** output. Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer. Clinical judgement, verification, and final sign-off remain with the reviewing clinician.

## License

MIT. See [`LICENSE`](./LICENSE).

## Maintainer

[Laszlo Szabo](https://github.com/Laszlo75) — consultant transplant surgeon, UK.
