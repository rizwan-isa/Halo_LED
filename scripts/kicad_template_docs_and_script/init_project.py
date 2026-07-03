#!/usr/bin/env python3
"""
Initialize a new KiCad project cloned from this template.

What it does:
- Replaces the template placeholder text (default: 'LED') with your new project name
  inside common project/config files.
- Renames files/folders that contain the placeholder in their *filename*.
- Patches workflow env vars (BaseFileName / PCBANumber / PCBNumber) safely (keeps YAML keys).

Typical use:
  python3 scripts/init_project.py --name FFM --pcba ES-A00098 --pcb ES-000144
  python3 scripts/init_project.py --name FFM --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_PLACEHOLDER = "LED"

EXCLUDE_DIRS = {
    ".git",
    "KiBotOutput",
    "ReviewDatapack",
    ".qodo",
    ".venv",
    "venv",
    "__pycache__",
}

# Files that are "text" but don't have extensions
TEXT_FILENAMES = {
    "fp-lib-table",
    "sym-lib-table",
}

# Extensions we treat as text and safe to search/replace
TEXT_EXTS = {
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini",
    ".kicad_sch", ".kicad_pcb", ".kicad_pro", ".kicad_prl", ".kicad_wks", ".kicad_sym",
    ".rules", ".drl", ".gbr", ".csv", ".html", ".xml",
    ".py", ".sh", ".bat", ".ps1",
}


@dataclass
class Change:
    path: Path
    action: str
    detail: str


def iter_paths(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        # Skip excluded dirs early
        parts = set(p.parts)
        if parts & EXCLUDE_DIRS:
            continue
        yield p


def is_text_file(p: Path) -> bool:
    if p.is_dir():
        return False
    if p.name in TEXT_FILENAMES:
        return True
    if p.suffix.lower() in TEXT_EXTS:
        return True
    return False


def safe_read_text(p: Path) -> str:
    # KiCad files are UTF-8; some tools may emit odd chars - ignore errors
    return p.read_text(encoding="utf-8", errors="ignore")


def safe_write_text(p: Path, content: str) -> None:
    p.write_text(content, encoding="utf-8")


def replace_in_file(p: Path, old: str, new: str, dry: bool) -> Change | None:
    if not is_text_file(p):
        return None

    txt = safe_read_text(p)
    if old not in txt:
        return None

    new_txt = txt.replace(old, new)
    if dry:
        return Change(p, "REPLACE", f"placeholder '{old}' -> '{new}'")
    safe_write_text(p, new_txt)
    return Change(p, "REPLACE", f"placeholder '{old}' -> '{new}'")


def rename_path(p: Path, old: str, new: str, dry: bool) -> Change | None:
    """
    Rename a file/folder if its name contains 'old'. Returns a Change if renamed.
    We rename deeper paths first by processing in reverse-length order elsewhere.
    """
    if old not in p.name:
        return None

    target = p.with_name(p.name.replace(old, new))
    if target == p:
        return None

    if dry:
        return Change(p, "RENAME", f"{p} -> {target}")

    # Ensure parent exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # If target exists, don't overwrite silently
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing path: {target}")

    p.rename(target)
    return Change(target, "RENAME", f"{p} -> {target}")


def patch_workflow_env(workflow_path: Path, updates: dict[str, str], dry: bool) -> list[Change]:
    """
    Safely patch workflow env keys:
      BaseFileName, PCBANumber, PCBNumber
    without corrupting YAML keys/indentation.

    Works on lines like:
      BaseFileName: LPDN_CB
      PCBANumber: 3E-A00098
      PCBNumber: 3E-000144
    """
    if not workflow_path.exists():
        return []

    txt = safe_read_text(workflow_path)
    original = txt

    changes: list[Change] = []

    for key, value in updates.items():
        # Match "key: whatever" preserving the "key: " prefix in group 1
        pat = re.compile(rf"(?m)^(\s*{re.escape(key)}\s*:\s*).*$")
        if not pat.search(txt):
            continue

        def repl(m: re.Match) -> str:
            prefix = m.group(1)
            # Preserve quotes if the original value looked quoted
            # (very simple heuristic)
            line = m.group(0)
            if '"' in line or "'" in line:
                # keep double-quotes for consistency
                return f'{prefix}"{value}"'
            return f"{prefix}{value}"

        txt = pat.sub(repl, txt, count=1)

    if txt != original:
        if dry:
            changes.append(Change(workflow_path, "PATCH", "workflow env updated (BaseFileName/PCBA/PCB)"))
        else:
            safe_write_text(workflow_path, txt)
            changes.append(Change(workflow_path, "PATCH", "workflow env updated (BaseFileName/PCBA/PCB)"))

    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="New project base name, e.g. FFM")
    ap.add_argument("--pcba", default="", help="PCBA number, e.g. ES-A00098")
    ap.add_argument("--pcb", default="", help="PCB number, e.g. ES-000144")
    ap.add_argument("--placeholder", default=DEFAULT_PLACEHOLDER, help=f"Template placeholder (default: {DEFAULT_PLACEHOLDER})")
    ap.add_argument("--root", default=".", help="Project root directory (default: current directory)")
    ap.add_argument("--dry-run", action="store_true", help="Print changes only; do not modify files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root path not found: {root}", file=sys.stderr)
        return 2

    old = args.placeholder
    new = args.name

    # 1) Patch workflows env vars FIRST (so global placeholder replace doesn't touch keys)
    workflow_dir = root / ".github" / "workflows"
    wf_changes: list[Change] = []
    if workflow_dir.exists():
        updates = {}
        # BaseFileName is almost always the project base name
        updates["BaseFileName"] = new
        if args.pcba:
            updates["PCBANumber"] = args.pcba
        if args.pcb:
            updates["PCBNumber"] = args.pcb

        for wf in list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml")):
            wf_changes.extend(patch_workflow_env(wf, updates, args.dry_run))

    # 2) Replace placeholder text inside text files
    replace_changes: list[Change] = []
    for p in iter_paths(root):
        ch = replace_in_file(p, old, new, args.dry_run)
        if ch:
            replace_changes.append(ch)

    # 3) Rename files/folders that contain the placeholder in their *filename*
    #    Process deeper paths first to avoid renaming parent then losing child reference.
    all_paths = [p for p in iter_paths(root)]
    all_paths.sort(key=lambda x: len(str(x)), reverse=True)

    rename_changes: list[Change] = []
    for p in all_paths:
        # if it was renamed already as a child of a renamed parent, it won't exist
        if not p.exists():
            continue
        try:
            ch = rename_path(p, old, new, args.dry_run)
        except FileExistsError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 3
        if ch:
            rename_changes.append(ch)

    # Summary
    def print_changes(title: str, lst: list[Change]) -> None:
        if not lst:
            return
        print(f"\n{title} ({len(lst)}):")
        for c in lst:
            print(f" - {c.action}: {c.path} :: {c.detail}")

    print_changes("Workflow patches", wf_changes)
    print_changes("Text replacements", replace_changes)
    print_changes("Renames", rename_changes)

    print("\nDone.")
    print(f"Placeholder '{old}' -> '{new}'.")
    if args.dry_run:
        print("(dry-run: no files were modified)")
    else:
        print("Tip: run `git status` then commit the changes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
