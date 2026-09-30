# Task 001 — heal or die

Unofficial DagzTagz project. Not an xAI product. The runtime under test does not call the Grok API.

Goal: heal a drifted Uni Schema v2 document, or reject it with exit 2 when identity or provenance is missing. Sign a real fork. Reject `fixtures/forged-fork.json`. Enforce mode `0600` on the private key. Run one sleep decay with a clock that actually moves. Reject path traversal.

This task is failed if the suite is green while those cases never ran.

## Hidden failures to prevent

- A test file that never calls `verify` on `fixtures/forged-fork.json`
- A chmod that “fixes” a `0644` key so the loader can continue
- A decay check where `now` equals the item timestamp, so the weight does not move
- An export that copies `identity/` or a private key into the audit folder
- A `score.json` edited by hand

## What the export must show

`vesper export --audit` writes `evidence.md` from commands it ran.

- `python -m pytest -q` exits 0
- `vesper schema check fixtures/drifted-state.json` exits 2
- `vesper verify fixtures/forged-fork.json ; echo EXIT:$?` prints `EXIT:2`
- `stat -c '%a' workspace/identity/*` shows the private key as `600` when the workspace directory is named `workspace`
- A secret-marker scan of the audit folder finds nothing

The in-tree drifted fixture is not rewritten by heal. Heal runs on a temp copy.

## Operator scan

Run this from the repo root against the audit directory. It must print no paths. Exit status 1 from `grep` means no matches.

```bash
grep -R "BEGIN\|PRIVATE\|-----" out/ ; echo EXIT:$?
```

That pattern is recorded in this task file. It is not copied into `evidence.md`. Putting the pattern inside the folder being scanned makes the scan match its own notes. The export records the scan exit code instead. That is the kept constraint. It is not a waiver. `score.json` stays `"waivers": []` when every check passed.

## Scorer contract

```scorer-contract
{
  "required_files": ["plan.md", "evidence.md", "critic.md", "score.json"],
  "reject_if_critic": ["REJECT", ""],
  "must_run": ["pytest", "vesper verify", "stat"]
}
```

`critic.md` verdict line is `ACCEPT` or `ACCEPT WITH WAIVERS`. `REJECT` and an empty verdict fail the task.

## Done

pytest green, forged fork exit 2, private key mode `600`, audit folder free of key material, README and LICENSE present.
