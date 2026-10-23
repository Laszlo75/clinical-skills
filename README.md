# Clinical Skills

> [!IMPORTANT]
> **This repository has moved.** The `clinical-evidence` plugin now lives in [Laszlo75/clinical-research-toolkit](https://github.com/Laszlo75/clinical-research-toolkit), in the `clinical-research` marketplace, alongside the data-science and clinical-writing plugins. This repository is no longer maintained; version 2.6.1 here is its last release.
>
> To switch, run:
>
> ```text
> /plugin marketplace remove clinical-skills
> /plugin marketplace add Laszlo75/clinical-research-toolkit
> /plugin install clinical-evidence@clinical-research
> ```

A Claude Code plugin marketplace hosting AI-assisted tools for clinical evidence synthesis and protocol review. Designed for the UK NHS context and shipped with ISO 42001 transparency disclaimers baked into every output.

## Plugins

| Plugin | Purpose |
|--------|---------|
| [`clinical-evidence`](./clinical-evidence/) | Systematic literature search + clinical protocol review. Bundles two co-designed skills that share a verified reference ledger. |

## Installation

Install from the new marketplace (see the notice above). The commands that used to be here installed this archived copy.

## Requirements

Each plugin documents its own dependencies. At minimum you will need:

- [Claude Desktop](https://claude.ai/download) (Claude Cowork or Claude Code) or another Claude client with MCP connector support
- The latest Claude Opus model (high effort) — see each plugin's README for the currently recommended model. Clinical reasoning, evidence appraisal, and reference integrity checks benefit from the strongest available model
- *Optional:* **pandoc** — only if your Claude environment cannot create Word documents natively
- **Python 3 + PyYAML** — used by the bundled reference verification and validation scripts

## AI Use & Governance (ISO 42001)

Every skill in this marketplace is AI-assisted and produces **draft** output. Every generated document carries a "DRAFT — NOT FOR CLINICAL USE" callout and a transparency disclaimer. Clinical judgement, verification, and final sign-off remain with the reviewing clinician.

## License

MIT. See [`LICENSE`](./LICENSE).

## Maintainer

[Laszlo Szabo](https://github.com/Laszlo75) — consultant transplant surgeon, UK.
