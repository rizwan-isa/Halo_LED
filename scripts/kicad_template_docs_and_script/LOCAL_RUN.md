# Running the workflow locally (macOS/Linux) using `act`

This is useful to test changes **before** pushing.

---

## Install prerequisites

### 1) Docker Desktop
Install and start Docker Desktop.

### 2) act
macOS:

```bash
brew install act
```

---

## Run the workflow locally

From your repo root:

```bash
act -W .github/workflows/gen_outputs.yml -j GRD
```

If you are on Apple Silicon and the container expects amd64:

```bash
act -W .github/workflows/gen_outputs.yml -j GRD --container-architecture linux/amd64
```

---

## Known issue: `upload-artifact` fails locally

When running via `act`, you are **not on GitHub’s runners**, so steps like `actions/upload-artifact@v4`
can fail with errors such as:

- `Unable to get the ACTIONS_RUNTIME_TOKEN env variable`
- `Failed to CreateArtifact: ECONNREFUSED`

### Fix (recommended): skip upload-artifact when ACT is running

In your workflow, wrap the upload step with:

```yaml
- name: Archive production artifacts
  if: ${{ env.ACT != 'true' }}
  uses: actions/upload-artifact@v4
  with:
    name: ReviewDatapack
    path: ReviewDatapack/
```

`act` automatically sets `ACT=true` inside the runner.

---

## Where outputs go

- `KiBotOutput/` – intermediate files produced by KiBot
- `ReviewDatapack/` – final datapack that you can open locally

---

## Debugging tips

- Use `--verbose` with act:

```bash
act -W .github/workflows/gen_outputs.yml -j GRD --verbose
```

- Find KiBot logs:
  - `KiBotOutput/kibot_debug.log`
