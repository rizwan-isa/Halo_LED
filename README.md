[comment]: <> (GitHub Repository Display Page)
[comment]: <> (Engineering Services Templates)
[comment]: <> (Rizwan Isa, 2024)

# Engineering Services — Project Templates

This repository contains reusable templates, skeletons, and process assets used by **Engineering Services** for delivering professional electronics, PCB, and mechanical CAD projects.

It is intended to:

- standardise project structure across client and personal work
- reduce setup time for new projects
- improve consistency of documentation, reviews, and manufacturing outputs
- make projects easy to navigate, audit, and hand over

---

## What’s Included

### Project Skeletons

Ready-made folder structures for common project types (e.g. hardware PCB project).

### Documentation Templates

Reusable documents for requirements capture, design notes, design reviews, and manufacturing handover.

### Gitignore Templates

Tool-specific `.gitignore` templates (KiCad, Altium, CAD exports) to keep repos clean and professional.

### Checklists

Practical checklists for:

- design readiness
- review readiness
- release readiness / manufacturing handover

---

## How To Use This Repo

### Recommended: Start a New Project From a Skeleton

1. Copy a skeleton into your new project workspace (example below).
2. Create a new Git repository for the project (one repo per project).
3. Commit the initial structure and start work.

Example (hardware PCB project):

```bash
# From your workspace
cp -R ~/EngineeringServices/01_Templates/engineering-services-templates/project_skeletons/hardware_project \
      ~/EngineeringServices/02_Freelance/Client_Project

cd ~/EngineeringServices/02_Freelance/Client_Project
git init
git add .
git commit -m "Initial project structure"
```

# KiCad Template – Local KiBot “Review Datapack” workflow

This repo is set up to generate a **Review Datapack** (PDFs, BoMs, Gerbers, drill files, etc.) using **KiBot**, driven by a **GitHub Actions workflow**.  
You can run the same workflow **locally** using [`act`](https://github.com/nektos/act) (which runs GitHub Actions inside Docker).

This README documents the **exact local workflow** we used, the **diagnostic steps**, and the **fixes** applied so the workflow runs end‑to‑end locally.

---

## Repo layout (relevant bits)

- `.github/workflows/gen_outputs.yml`  
  GitHub Actions workflow that runs KiBot + packages outputs into a datapack.
- `src/config.kibot.yaml`  
  Main KiBot config entrypoint.
- `src/kibot/test.yaml`  
  “Collector” config that imports all outputs. You can comment out imports here to debug.
- `src/kibot/outputs/*.yaml`  
  Individual KiBot output definitions (Gerbers, drill, BoM, PDFs, etc.).
- `KiBotOutput/`  
  Output folder created by the workflow.
- `ReviewDatapack/`  
  Final datapack folder created by the workflow.

---

## Prerequisites (local)

### 1) Docker

- Install Docker Desktop and ensure it’s running.

### 2) act

On macOS:

```bash
brew install act
```

Check it works:

```bash
act --version
docker --version
```

> **Note (Apple Silicon / M1/M2/M3):**  
> `act` may run containers as `arm64` by default. If you ever hit image compatibility issues, you can force:
>
> ```bash
> act --container-architecture linux/amd64 ...
> ```

---

## Quick start (run the workflow locally)

From the repo root:

```bash
act -W .github/workflows/gen_outputs.yml -j GRD
```

Typical useful variations:

```bash
# Re-run without rebuilding everything (often faster)
act -W .github/workflows/gen_outputs.yml -j GRD -r

# If you need amd64 on Apple Silicon
act -W .github/workflows/gen_outputs.yml -j GRD --container-architecture linux/amd64
```

After success, you should have:

- `KiBotOutput/` populated (PDFs, BoMs, Gerbers, drill files, logs, etc.)
- `ReviewDatapack/Datapack_<...>/` populated (packaged datapack structure)

---

## How the KiBot configuration is wired

### Main entrypoint

`src/config.kibot.yaml` imports:

- `kibot/test.yaml`

### Collector / “test” config

`src/kibot/test.yaml` imports many outputs, e.g.

- `outputs/archive_prj.yaml`
- `outputs/drill.yaml`
- `outputs/gerbers.yaml`
- `outputs/pdf_schematic.yaml`
- etc.

**Debug tip:** you can comment out outputs to isolate problems.

Example (disabling 3D output while debugging):

```yaml
import:
  - outputs/pcb_2d.yaml
  # - outputs/pcb_3d.yaml   # disabled for debug
  - outputs/pdf_pcb.yaml
```

---

## Step-by-step diagnostics & fixes (what we actually did)

### Step 1 — Confirm where KiBot logs are written

We saw the workflow failing at:

- **“Copy kibot run log file into Reports folder”**  
  with:
  ```
  cp: cannot stat 'kibot_log.log': No such file or directory
  ```

**Diagnosis commands (local):**

```bash
ls -al
ls -al KiBotOutput || true

# Find any kibot logs/debug output that actually exists
find . -maxdepth 3 -type f \( -iname "*kibot*log*" -o -iname "*kibot*debug*" \) -print
```

What we found:

- `KiBotOutput/kibot_debug.log` existed
- `KiBotOutput/kibot_log.log` did **not** exist yet

**Fix applied (in workflow):**  
Make KiBot write an explicit log file that the later `cp` step expects.

In `.github/workflows/gen_outputs.yml` we ensured the KiBot step includes:

```yaml
additional_args: "-d -vv -L KiBotOutput/kibot_log.log"
```

Now the copy step succeeds because the file exists:

- `KiBotOutput/kibot_log.log`

> If you prefer not to use `-L`, an alternative is redirecting output, e.g.  
> `kibot ... |& tee KiBotOutput/kibot_log.log` (when running KiBot directly).

---

### Step 2 — Diagnose KiBot config errors (missing output type)

We hit this KiBot error in `KiBotOutput/kibot_debug.log`:

```
ERROR: Output `Run KiBot` needs a type
```

That error means:

- KiBot parsed an entry under `outputs:` where `name:` existed but `type:` was missing.

**How we inspected the exact location:**

```bash
# Show the section around the error
nl -ba KiBotOutput/kibot_debug.log | sed -n '460,520p'

# See config/import chain in the log
grep -nE "Using configuration file|Parsing imports|Outputs loaded from" KiBotOutput/kibot_debug.log | tail -n 80
```

**How to find the broken output in your repo:**

```bash
# Search for the output name (example)
grep -RIn "Run KiBot" src/kibot

# Search for any output missing a type (quick manual check)
grep -RIn "^\s*-\s*name:" src/kibot
```

**What to fix:** ensure every output has a `type:`.

Correct pattern:

```yaml
outputs:
  - name: "something"
    type: "pdf" # <- must exist
```

> If you still can’t find it, a YAML indentation error (or accidentally importing a non‑KiBot YAML) can cause odd parsing.  
> In that case, temporarily comment out imports in `src/kibot/test.yaml` until the error disappears, then narrow down.

---

### Step 3 — Fix `upload-artifact` failures when running locally with act

Once the datapack generation was working, the job still failed at:

- **“Archive production artifacts”** using `actions/upload-artifact@v4`

Errors seen included:

- `Unable to get the ACTIONS_RUNTIME_TOKEN env variable`
- `Failed to CreateArtifact ... ECONNREFUSED`

**Root cause:**  
`act` is not GitHub Actions. `upload-artifact` expects GitHub’s artifact service + runtime token, which does not exist locally.

**Fix applied (Option A):**  
Skip the upload step when running under `act` using `env.ACT` (act sets this).

In `.github/workflows/gen_outputs.yml`:

```yaml
- name: Archive production artifacts
  if: ${{ !env.ACT }}
  uses: actions/upload-artifact@v4
  with:
    name: ReviewDatapack
    path: ReviewDatapack
```

✅ With this change, local runs complete successfully and you just take the files from `ReviewDatapack/` yourself.

---

## Common shell gotchas (zsh)

### Inline comments need a space

This fails:

```bash
ls# comment
```

Use:

```bash
ls # comment
```

### Parentheses in `find`

In zsh, parentheses should be escaped:

```bash
find . -maxdepth 3 -type f \( -iname "*kibot*log*" -o -iname "*kibot*debug*" \) -print
```

---

## Where to change things

### Change project metadata used in the workflow

Edit `.github/workflows/gen_outputs.yml` `env:` section, e.g.:

- `BaseFileName`
- `PCBANumber`
- `PCBNumber`
- `Timezone`

### Enable/disable specific KiBot outputs

Edit `src/kibot/test.yaml` import list and comment out modules you don’t want (or while debugging).

---

## Verify outputs

After a local run:

```bash
ls -al KiBotOutput
ls -al ReviewDatapack
```

Typical important files:

- PDFs: schematic / assembly docs
- Manufacturing: gerbers, drill
- BoMs: CSV + HTML
- Logs: `KiBotOutput/kibot_debug.log`, `KiBotOutput/kibot_log.log`

---

## Troubleshooting checklist

1. **Workflow fails copying a file**

- Run `find` to confirm the file exists and path matches.
- Fix the workflow to point at the real file path.

2. **KiBot complains about config**

- Read `KiBotOutput/kibot_debug.log`
- Use `nl -ba ... | sed -n '...p'` around the error
- Narrow down by commenting out imports in `src/kibot/test.yaml`

3. **upload-artifact fails locally**

- Confirm the step is guarded with:
  ```yaml
  if: ${{ !env.ACT }}
  ```

---

## Appendix — Running KiBot manually (optional)

If you want to run KiBot directly (outside GitHub Actions), from repo root:

```bash
kibot -c src/config.kibot.yaml -d -vv -L KiBotOutput/kibot_log.log
```

> This requires KiBot installed on your machine (the workflow does not).

# Local Workflow Notes (Detailed)

This file is a “deep dive” version of the local run instructions from the root README.

## 1) Install tools

### macOS (Homebrew)

```bash
brew install act
brew install --cask docker
```

Start Docker Desktop, then:

```bash
docker info
act --version
```

## 2) Run the GRD job

```bash
act -W .github/workflows/gen_outputs.yml -j GRD
```

## 3) Inspect results

```bash
tree -L 2 KiBotOutput || ls -R KiBotOutput
tree -L 3 ReviewDatapack || ls -R ReviewDatapack
```

## 4) Debug KiBot problems fast

### A) Confirm config + import chain

```bash
grep -nE "Using configuration file|Parsing imports|Outputs loaded from" KiBotOutput/kibot_debug.log | tail -n 80
```

### B) Show the error context

```bash
nl -ba KiBotOutput/kibot_debug.log | sed -n '1,140p'
```

### C) Binary search outputs

Edit `src/kibot/test.yaml` and comment out half the imports; rerun; repeat until you isolate the failing output module.

## 5) Why we skip artifact upload locally

`actions/upload-artifact@v4` needs GitHub’s runtime token and artifact service.  
`act` doesn’t provide that, so we guard the step:

```yaml
if: ${{ !env.ACT }}
```

This is the correct approach for local debug and CI parity:

- CI run on GitHub uploads artifacts
- Local run produces artifacts on disk only

---

## Creating a new project from this template

### Option 1: GitHub UI (recommended)

1. On GitHub, click **Use this template**
2. Create the new repository (e.g. `FFM`)
3. Clone it locally

```bash
git clone <your-new-repo-url>
cd <your-new-repo>
```

4. Initialize/rename the project (this updates filenames AND workflow env vars)

```bash
python3 scripts/init_project.py --name FFM --pcba ES-A00098 --pcb ES-000144
```

5. Commit the changes

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
