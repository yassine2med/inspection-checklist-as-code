"""Command line: python -m checklistpdf checklist.yaml [--pdf out.pdf]."""
from __future__ import annotations

import argparse
import sys

from .checklist import ChecklistError, count_items, load_checklist, render_pdf, render_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="checklistpdf", description=__doc__)
    parser.add_argument("yaml_file")
    parser.add_argument("--pdf", help="write a PDF to this path")
    args = parser.parse_args(argv)
    try:
        data = load_checklist(args.yaml_file)
    except (ChecklistError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    lines = render_text(data)
    if args.pdf:
        with open(args.pdf, "wb") as handle:
            handle.write(render_pdf(lines))
        print(f"wrote {args.pdf}: {count_items(data)} items, {len(lines)} lines")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
