#!/usr/bin/env python3
"""
Build meetings.json from the meetings/ directory.

For every folder in meetings/ that contains a meta.json:
  - validate it (title + date required, date must be YYYY-MM-DD)
  - copy _template/index.html into the folder if it has no index.html yet
  - add it to the site index

Result: meetings.json at the repo root, sorted oldest -> newest.
Run manually with `python3 scripts/build_index.py`, or let the
GitHub Action run it on every push.
"""
import json
import shutil
import sys
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEETINGS_DIR = ROOT / "meetings"
TEMPLATE_PAGE = ROOT / "_template" / "index.html"
OUTPUT = ROOT / "meetings.json"


def fail(errors):
    print("\n!! meetings.json NOT written. Fix these problems:\n", file=sys.stderr)
    for e in errors:
        print(f"   - {e}", file=sys.stderr)
    sys.exit(1)


def main():
    entries, errors = [], []

    if not MEETINGS_DIR.exists():
        MEETINGS_DIR.mkdir()

    for folder in sorted(p for p in MEETINGS_DIR.iterdir() if p.is_dir()):
        meta_path = folder / "meta.json"
        if not meta_path.exists():
            errors.append(f"{folder.name}: no meta.json (copy one from _template/)")
            continue

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{folder.name}/meta.json: invalid JSON ({e})")
            continue

        title = meta.get("title", "").strip()
        date_str = str(meta.get("date", "")).strip()
        if not title:
            errors.append(f"{folder.name}/meta.json: missing \"title\"")
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            errors.append(f"{folder.name}/meta.json: \"date\" must be YYYY-MM-DD (got \"{date_str}\")")
        if not title or not date_str:
            continue

        # Self-heal: give the folder a page if it doesn't have one yet.
        page = folder / "index.html"
        if not page.exists():
            shutil.copy(TEMPLATE_PAGE, page)
            print(f"   + created {folder.name}/index.html from template")

        slides = meta.get("slides", "slides.pdf")
        entries.append({
            "slug": folder.name,
            "path": f"meetings/{folder.name}/",
            "title": title,
            "date": date_str,
            # Optional "order" sequences multiple talks on the SAME date
            # (lower = earlier in the session). Defaults to 0.
            "order": meta.get("order", 0),
            "project": meta.get("project", "General"),
            "summary": meta.get("summary", ""),
            "hasSlides": (folder / slides).exists(),
        })

    if errors:
        fail(errors)

    entries.sort(key=lambda m: (m["date"], m["order"], m["slug"]))
    OUTPUT.write_text(
        json.dumps(
            {"generated": date.today().isoformat(), "count": len(entries), "meetings": entries},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"OK meetings.json written: {len(entries)} meeting(s), "
          f"{len(set(m['project'] for m in entries))} project thread(s).")


if __name__ == "__main__":
    main()
