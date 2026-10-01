# Audit export

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

`vesper export --audit DIR` writes a folder a stranger can read. The folder is the record of the checks. It is not a copy of your chat, and it is not a copy of `identity/`.

The directory is mode `0700`. Each file in it is mode `0600`.

## What each file is for

| File | One sentence |
|------|----------------|
| `plan.md` | States the checks this export promised to run, and says a green suite that skipped them would be quitting early. |
| `evidence.md` | Shows each command that was run, with its exit code, stdout, and stderr. |
| `critic.md` | Gives a short review under the headings `BLOCKERS`, `RISKS`, `NITS`, `MISSING EVIDENCE`, `WAIVERS`, and `VERDICT`. |
| `score.json` | Holds the machine-readable pass or fail for task `001-heal-or-die`. |
| `state_hash.txt` | Holds the hex SHA-256 of the canonical workspace state, plus a newline. |
| `fork_verified.json` | Holds a byte copy of the verified head snapshot, or the JSON value `null` when there is no verified head or the copy was withheld. |

A stranger can read this folder without the chat log because the plan says what was promised, the evidence shows the commands, and the score says whether they passed. The notes inside a copied fork are the snapshot, not the terminal session that typed them.

## `score.json`

The keys are written in this order, without sorting:

1. `task_id` — always `001-heal-or-die`
2. `pass` — true or false
3. `checks` — the seven booleans below, in this order
4. `waivers` — a list, `[]` on a clean run

The check names are `schema_heal_or_reject`, `forged_signature_rejected`, `parent_chain_ok`, `key_mode_enforced`, `memory_decay_ran`, `path_traversal_rejected`, and `no_secrets_in_export`.

`pass` is true only when every check is true and the pytest child exited 0. When export is already running inside pytest (`PYTEST_CURRENT_TEST` is set), it does not start another pytest, and that part stays true. When it does start pytest, the child environment includes `VESPER_EXPORT_CHILD=1`. Nothing else in v0.1 reads that name. The evidence line for the suite is `python -m pytest -q`.

The verdict printed on the terminal, and stored under `VERDICT` in `critic.md`, is `ACCEPT`, `ACCEPT WITH WAIVERS`, or `REJECT`. `ACCEPT` does not contain the letters `REJECT`. Waivers produce `ACCEPT WITH WAIVERS`. A failed check produces `REJECT` and exit 2 (`vesper: audit checks failed`). A clean walk should have `"waivers": []`.

The seven checks use fixtures and temporary workspaces. They do not prove that your personal head was the file copied into the folder. After `verify --head` succeeds, `fork_verified.json` is a byte copy of `forks/<name>.json`. If the head does not verify, that file is `null` followed by a newline, and the other checks can still pass. Read the file before you treat the folder as a copy of your snapshot.

## What must not appear

The folder must not contain:

- a directory named `identity`
- a file whose name ends in `.priv`, including `edcsa-p256.priv`
- a file named `hmac.key`
- PEM-shaped text

Export does not copy `identity/`. If the verified fork itself contains PEM-shaped text, the program writes `fork_verified.json` as JSON `null`, sets `no_secrets_in_export` to false, sets `pass` to false, and records the line `secret-marker scan found a hit; the fork copy was withheld`. That line does not repeat the marker.

The operator search that looks for those markers lives in [tasks/001-heal-or-die.md](../tasks/001-heal-or-die.md), inside the fence tagged `scorer-contract`. Copying that search into the audit folder would make the scan match its own notes. `evidence.md` records the scan as an exit code. Exit 1 from that scan means no hits.

When the workspace directory is literally named `workspace`, one evidence command is `stat -c '%a' workspace/identity/*`. That command's output is modes, not key bytes.

The forged-fixture line in evidence is exactly:

```text
vesper verify fixtures/forged-fork.json; echo EXIT:$?
```

The stdout of that command must contain `EXIT:2`.

## The sample

[examples/passing-audit/](../examples/passing-audit/) is a folder produced by an earlier successful export. It contains a public key and a signature. It does not contain a private key.

`fork_verified.json` in that sample is a snapshot whose signed name is `alpha`. `vesper verify` of the path `fork_verified.json` returns reason `name`, because the stem is not `alpha`. Copy the bytes to a file named `alpha.json` in the same directory as any parent it names, or verify the workspace fork, and the stamp can be checked. ECDSA verify uses the public point inside the file.

The pytest transcript inside that sample says `58 passed`. That number is from the run that wrote the sample. It is not a promise about today's suite. Do not regenerate the sample to chase a new count. A new export belongs in `out/`, which is gitignored.

## Command

```bash
vesper --workspace ./workspace verify --head
vesper --workspace ./workspace export --audit ./out
```

What good looks like: `verify ok`, then `ACCEPT`, then the `out` path, exit 0. `out/score.json` has `"pass": true` and `"waivers": []`. `find out -name 'edcsa-p256.priv' -o -name 'hmac.key' -o -name 'identity'` prints nothing.

What failure means: `REJECT` and exit 2. Open `out/evidence.md` and read the command whose exit code is unexpected. A withheld fork is a failed score on purpose, even after the copy has been replaced with `null`.
