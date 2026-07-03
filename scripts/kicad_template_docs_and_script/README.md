# KiCad Hardware Project Template (Engineering Services)

This repo is a **GitHub Template Repository** for starting new KiCad hardware projects with:

- A consistent folder structure
- KiBot-based output generation (BoMs, PDFs, gerbers, drill, etc.)
- A GitHub Action workflow (and optional local runs via `act`)
- A one-command project initializer script that renames the template placeholder

---

## What you get

- `src/` contains the KiCad project files (schematic, PCB, libraries, page layout, theme, etc.)
- `.github/workflows/` contains the **Generate Review Datapack** workflow
- `Scripts/init_project.py` turns the template into a real project (renames files + updates workflow env vars)
- Output folders (generated):
  - `KiBotOutput/` (intermediate)
  - `ReviewDatapack/` (final datapack folder)

> Note: `KiBotOutput/` and `ReviewDatapack/` should stay ignored (they are generated artifacts).

---

## Critical: do NOT ignore required template assets

If you ignore these, GitHub Actions will fail (because the files won't exist on the runner):

- `src/*.kicad_wks` (page layout / worksheet)
- `src/*Theme.json` (KiCad theme JSON)
- Your logo file if it is referenced by docs or templates (e.g. `ES_Logo_V2.svg`)

### How to check why a file is ignored

```bash
git check-ignore -v src/LED_SheetTemplate_3Coments.kicad_wks
git check-ignore -v src/LEDTheme.json
git check-ignore -v ES_Logo_V2.svg
```

### Fix: unignore and commit the files

1) Edit `.gitignore` and remove the lines that ignore them, **or** add exceptions at the bottom:

```gitignore
# --- allow required template assets ---
!ES_Logo_V2.svg
!src/*.kicad_wks
!src/*Theme.json
```

2) Force add (needed if Git already considers them ignored):

```bash
git add -f ES_Logo_V2.svg \
  src/LED_SheetTemplate_3Coments.kicad_wks \
  src/LEDTheme.json
git commit -m "Add required template assets (logo, page layout, theme)"
git push
```

> SourceTree typically doesn’t show ignored files as “changed”. Use Terminal for this step.

---

## Creating a new project from this template

### Option 1: GitHub UI (recommended)

1) On GitHub, click **Use this template**
2) Create the new repository (e.g. `FFM`)
3) Clone it locally

```bash
git clone <your-new-repo-url>
cd <your-new-repo>
```

4) Initialize/rename the project (this updates filenames AND workflow env vars)

```bash
python3 Scripts/init_project.py --name FFM --pcba ES-A00098 --pcb ES-000144
```

5) Commit the changes

```bash
git status
git commit -am "Initialize project FFM from template"
git push
```

### Option 2: GitHub CLI (fast)

```bash
gh repo create FFM --template <ORG>/<TEMPLATE_REPO> --public
git clone <your-new-repo-url>
cd FFM
python3 Scripts/init_project.py --name FFM --pcba ES-A00098 --pcb ES-000144
git commit -am "Initialize project FFM from template"
git push
```

---

## Local workflow runs (optional)

See: `docs/LOCAL_RUN.md`

---

## Making it feel like a “true template” (rename from GitHub only)

GitHub can’t automatically prompt/rename on “Use this template”, but you *can* add an **Init Project** workflow
that you run once from the Actions tab with inputs (project name, PCBA, PCB). It will rename and commit for you.

See: `docs/TEMPLATE_USAGE.md`
