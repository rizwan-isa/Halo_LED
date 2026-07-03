# Turning this into a “true template” (GitHub-only initialization)

Goal: after you click **Use this template**, you can initialize/rename the project **from GitHub Actions**
without running anything locally.

You do this by adding a workflow that:
1) Checks out the repo
2) Runs `scripts/init_project.py` with inputs
3) Commits + pushes the renamed files

---

## 1) Add this workflow file

Create:

`.github/workflows/init_from_template.yml`

```yaml
name: "Initialize Project (one-time)"

on:
  workflow_dispatch:
    inputs:
      project_name:
        description: "New project base name (e.g. FFM)"
        required: true
        type: string
      pcba_number:
        description: "PCBA number (e.g. ES-A00098)"
        required: false
        type: string
      pcb_number:
        description: "PCB number (e.g. ES-000144)"
        required: false
        type: string
      placeholder:
        description: "Template placeholder string"
        required: false
        default: "HB"
        type: string

permissions:
  contents: write

jobs:
  init:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: Run initializer
        run: |
          python3 Scripts/init_project.py \
            --name "${{ inputs.project_name }}" \
            --pcba "${{ inputs.pcba_number }}" \
            --pcb "${{ inputs.pcb_number }}" \
            --placeholder "${{ inputs.placeholder }}"

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git commit -m "Initialize project ${{ inputs.project_name }} from template" || echo "No changes to commit"
          git push
```

---

## 2) Use it

1) Create a new repo using **Use this template**
2) Go to **Actions** → **Initialize Project (one-time)** → **Run workflow**
3) Fill in the fields (project name, PCBA, PCB)
4) The workflow will commit/push the rename automatically

---

## Notes / best practice

- After initialization, you can delete this workflow from the new repo, or leave it but avoid re-running it.
- If you want to prevent accidental re-runs, add a “marker file” check (e.g. `.template_initialized`).
