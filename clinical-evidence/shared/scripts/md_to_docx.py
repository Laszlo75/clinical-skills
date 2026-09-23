#!/usr/bin/env python3
"""Convert the finished Markdown document to .docx in the house style.

Usage:
    python md_to_docx.py <input.md> <output.docx> --reference-doc <reference.docx> [--install]

Why a script: converting Markdown with pandoc costs no model tokens, whereas having
the model generate the Word file as code costs many thousands. Tries, in order:

  1. `pandoc` on PATH;
  2. the pandoc bundled with the `pypandoc_binary` Python package;
  3. with --install: `pip install --quiet pypandoc_binary`, then 2 again.

Exit codes: 0 — written; 3 — no pandoc available (the skill then falls back to the
environment's built-in Word-document capability); 1 — pandoc ran but failed; 2 — bad input.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _pandoc_path() -> str | None:
    found = shutil.which("pandoc")
    if found:
        return found
    try:
        import pypandoc  # type: ignore

        return pypandoc.get_pandoc_path()
    except Exception:
        return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--reference-doc", type=Path, required=True)
    p.add_argument("--install", action="store_true", help="pip-install pypandoc_binary if needed")
    args = p.parse_args()

    if not args.input.exists():
        sys.stderr.write(f"ERROR: input not found: {args.input}\n")
        return 2
    if not args.reference_doc.exists():
        sys.stderr.write(f"ERROR: reference doc not found: {args.reference_doc}\n")
        return 2

    pandoc = _pandoc_path()
    if not pandoc and args.install:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pypandoc_binary"],
                       check=False, capture_output=True)
        pandoc = _pandoc_path()
    if not pandoc:
        print("NO_PANDOC: pandoc is not available — use the built-in Word-document capability instead.")
        return 3

    cmd = [pandoc, str(args.input), "-o", str(args.output),
           f"--reference-doc={args.reference_doc}", "--from=markdown+yaml_metadata_block",
           "--to=docx"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"ERROR: pandoc failed: {result.stderr.strip()}\n")
        return 1
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
