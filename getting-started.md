# Getting Started

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product.

**This runtime does not call the Grok API.** Dry `pytest` does not spend model credit. Live Grok Build use, if you choose it later, is your bill. DagzTagz owns the repo.

Phase 1 is a local CLI. It signs JSON files on disk.

## Read this before you create a key

These sentences say what the software is. They are not legal advice. They do not promise a particular outcome if someone disputes your use of it. Read [LICENSE](LICENSE) for the binding warranty text.

vesper-runtime is a local development and provenance tool. You use it to keep notes on disk and to sign a JSON snapshot so a later reader can check the signature.

It is provided **AS IS**. Apache-2.0 gives no warranty of fitness for a particular purpose, no warranty of merchantability, and no warranty of non-infringement. You use it at your own risk. The authors and DagzTagz contributors are not taking custody of a key, a file, or a decision you make with one.

You are responsible for:

- choosing where the workspace lives
- keeping the private key mode `0600`
- backups, if you want them
- not publishing the private key
- what you sign

A passing `verify` means the bytes match a signature. It does not prove a legal identity. It is not a certificate. It is not a lab result. It is not a payment.

This program does not fill these roles:

- a consumer crypto-asset wallet
- a money transmitter
- a security offering
- an official scientific instrument
- an anonymity system
- an xAI, SpaceXAI, or Grok product

There is no HIPAA claim, no SOC 2 claim, and no certification. Privacy is the privacy of this Unix account and this disk. The CLI does not open a network connection. It does not call the Grok API.

Do not import the key into a wallet. Do not ask this tool to sign a transaction. There is no address, no seed phrase, no balance, and no payment command.

## Requirements

- Ubuntu (these commands are written for this VM)
- Python 3.11 or newer (`python3 --version`)
- `git`
- A virtual environment you control

No API key. No `.env`. No network during `pytest` or `vesper`.

## Install

```bash
git clone https://github.com/DagzTagz/vesper-runtime.git
cd vesper-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
vesper --help
```

What good looks like: pytest prints a count of passed tests and exits 0. `vesper --help` prints the command list and exits 0.

What failure means:

| What you see | Meaning |
|--------------|---------|
| `python3: command not found` | Install Python 3.11+ before the venv step. |
| `No module named pytest` | The venv is not active, or `pip install -e ".[dev]"` did not finish. |
| pytest failures | Do not init a workspace on top of a red suite. Read the first failure. |
| `vesper: command not found` | Activate `.venv` again. The script is installed into that venv, not into the system. |

`python -m vesper` is the same entry as the `vesper` script.

## Dry path

`--dry-run` prints the files `init` or `fork` would write. It does not create them.

```bash
vesper --dry-run init --workspace ./workspace --callsign nova
```

What good looks like: lines that start with `dry-run:` and no `workspace/` directory afterwards.

```bash
test ! -d workspace && echo "dry-run wrote nothing"
```

## Create a workspace

Do this only after the dry-run above printed `dry-run:` and did not create a folder.

Put the workspace on a normal Unix disk, in a directory only your user should use. `./workspace` inside the clone is the path this guide uses. It is listed in `.gitignore`.

Avoid these places:

- `/tmp`, or any other world-writable directory
- a shared folder, a USB stick formatted without Unix permissions, or a cloud-sync folder
- a path you later `git add -f`

Unix modes do not protect a file on a disk that ignores them. If the sync tool copies the folder, it copies the key.

```bash
vesper init --workspace ./workspace --callsign nova
stat -c '%a %n' workspace workspace/identity workspace/identity/* workspace/state.json workspace/forks
```

What good looks like: stdout says `initialized`, and `stat` prints:

| Path | Mode | What it is |
|------|------|------------|
| `workspace/identity` | `700` | Only your user can open this directory |
| `workspace/identity/edcsa-p256.priv` | `600` | Private key. Secret. |
| `workspace/identity/public.json` | `644` | Public key id and public point. Safe to show. |
| `workspace/state.json` | `600` | Your notes. Treat as private. |
| `workspace/forks` | `700` | Signed snapshots live here |

The private-key filename is `edcsa-p256.priv` in v0.1. That spelling is the layout name.

If `ecdsa` did not import, the secret file is `identity/hmac.key` at mode `600` instead. There is no public point in that case. Treat `hmac.key` as secret too. You need it to verify, not only to sign.

What failure means:

| Exit | Meaning |
|------|---------|
| 1 | Usage. A required flag is missing, or two `--workspace` values disagree. |
| 2 | The callsign is empty, too long, or contains `/`, `\`, or `..`. |
| 3 | The identity directory already exists, or the process cannot create mode `0700` / `0600`. |

If the private key is not `600`, or the identity directory is not `700`, stop. Do not `chmod` it and keep using it. A key that was readable by other users is burned.

```bash
if [ -f workspace/identity/edcsa-p256.priv ]; then shred -u -n 1 workspace/identity/edcsa-p256.priv; fi
if [ -f workspace/identity/hmac.key ]; then shred -u -n 1 workspace/identity/hmac.key; fi
rm -rf workspace
```

Then run `init` again on a disk that can hold mode `0600`. `shred` overwrites the file once and unlinks it. On an SSD, a copy-on-write disk, or some VM disks, that overwrite may not reach the old blocks. This tool does not wipe free space.

Do not `cat`, `less`, or screenshot the private key. Do not paste it into a chat, an issue, or a model. The tool does not print it. A person still can.

`workspace/` is gitignored. Do not force-add it.

## Keep or destroy the key

The public file `public.json` is the half you can show. The `.priv` file is the half you must not show. ECDSA snapshots also store the public point, so an old fork can be checked after the private key is gone. You need the private key only to sign a new fork.

To keep a copy offline, outside the git repo:

```bash
install -d -m 700 "$HOME/vesper-key-backup"
if [ -f workspace/identity/edcsa-p256.priv ]; then
  install -m 600 workspace/identity/edcsa-p256.priv "$HOME/vesper-key-backup/edcsa-p256.priv"
fi
if [ -f workspace/identity/hmac.key ]; then
  install -m 600 workspace/identity/hmac.key "$HOME/vesper-key-backup/hmac.key"
fi
install -m 644 workspace/identity/public.json "$HOME/vesper-key-backup/public.json"
stat -c '%a %n' "$HOME/vesper-key-backup" "$HOME/vesper-key-backup"/*
```

What good looks like: the backup directory is `700`, the secret file is `600`, and `public.json` is `644`. Do not email that directory. Do not put it inside the clone.

To stop using the key and remove the workspace:

```bash
if [ -f workspace/identity/edcsa-p256.priv ]; then shred -u -n 1 workspace/identity/edcsa-p256.priv; fi
if [ -f workspace/identity/hmac.key ]; then shred -u -n 1 workspace/identity/hmac.key; fi
rm -rf workspace
test ! -e workspace && echo "workspace removed"
```

What good looks like: `workspace removed`. Same limit as above: `shred` is not a free-space wipe.

v0.1 has no rotate command and no in-place key swap. To start over, destroy or archive the old `identity/`, then `init` a new workspace. That creates a new key and a new `kid`. Do not copy the old `.priv` file into the new `identity/` directory.

If a private key was mode `644` or looser, was committed, or was pasted into a chat, treat it as public. Stop signing with it. Init a new workspace.

## Remember, sleep, fork

```bash
vesper --workspace ./workspace remember --text "first note" --valence 0.6
vesper --workspace ./workspace sleep --now 1700003600
vesper --workspace ./workspace fork --name alpha --now 1700003601
vesper --workspace ./workspace verify --head
vesper verify workspace/forks/alpha.json
```

`--now` is a Unix timestamp. Tests and audits pass it so the clock does not depend on the wall. If you omit it, the kernel uses the current time.

What good looks like: `remember` prints an id like `m-` plus hex. `sleep` prints `slept`. `fork` prints the path of `forks/alpha.json`. `verify` prints `verify ok` and exits 0.

ECDSA verify reads the public point stored in the fork. It does not need `./workspace`. HMAC verify (only when init could not import `ecdsa`) needs `--workspace` pointed at the identity that signed the file.

What failure means:

- `vesper: bad_signature` and exit 2: the signature does not match the canonical body, or the key id does not match the public point.
- `vesper: parent_missing` and exit 2: `parent_id` is set and the parent file is not beside this fork. `--allow-orphan` is an explicit waiver. The export records it. Do not use it to paper over a lost parent.
- `vesper: replay` and exit 2: the file is an older snapshot presented as a newer head, or the state hash matches the parent.
- `vesper: name` and exit 2: the filename stem is not the signed `name`, or the name contains a path.

Memory, short version:

- STM keeps 100 items. The oldest `(ts, id)` drops on overflow.
- Semantic weight is multiplied by `exp(-0.02 * hours)` on sleep. An item drops when weight is below 0.02 and valence is below 0.4, unless it is pinned.
- Graph edges below weight 0.05 are pruned unless pinned. There is no graph decay in v0.1.
- An item is promoted to LTM when `weight * valence * user_weight >= 0.45`, or when it is pinned. LTM is not auto-deleted. Duplicate LTM ids keep the max weight.
- `user_weight` defaults to 1.0 and must sit in `(0, 2]`.
- If `--now` equals the item timestamp, decay does not move the weight. That is the control, not the proof.

`vesper memory export` prints the four lists as JSON. It does not write the audit folder. The audit command is `vesper export`.

## Check and heal a schema file

```bash
vesper schema check fixtures/drifted-state.json ; echo EXIT:$?
```

What good looks like for that fixture: exit 2. The file is missing tier lists on purpose. The command does not rewrite it.

Heal a **copy**:

```bash
mkdir -p /tmp/vesper-heal
cp fixtures/drifted-state.json /tmp/vesper-heal/state.json
vesper schema heal /tmp/vesper-heal/state.json --write
```

What good looks like: the copy gains empty `semantic`, `graph`, and `ltm` lists, and the STM item gains `tier` and `pinned`. `character.id` stays `char-drift`. `builder_note` stays.

What failure means: exit 2 and the file unchanged. Heal will not invent `universe_id`, `schema_version`, `character.id`, `callsign`, `straussian_level`, or `forks`. A missing memory object is also a reject.

## Verify the forged fixture

```bash
vesper verify fixtures/forged-fork.json ; echo EXIT:$?
```

What good looks like: `vesper: bad_signature` and `EXIT:2`.

Exit 0 on that file means the check did not run. Do not treat the suite as done.

## Export an audit folder

```bash
vesper --workspace ./workspace export --audit ./out
```

What good looks like: stdout ends with `ACCEPT` and the `out` path. `out/score.json` has `"pass": true`. `out/` contains `plan.md`, `evidence.md`, `critic.md`, `score.json`, `state_hash.txt`, and `fork_verified.json`.

What failure means: exit 2 and `REJECT` or `ACCEPT WITH WAIVERS` in the critic. Read `evidence.md` for the command that failed. The folder must not contain `identity/` or a private key.

```bash
find out -name 'edcsa-p256.priv' -o -name 'hmac.key' -o -name 'identity'
```

What good looks like: that `find` prints nothing.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success. `verify` accepted the file. |
| 1 | Usage. |
| 2 | Schema, validation, or signature failure. |
| 3 | Missing file, bad directory mode, or a private key that is not `0600`. |

The tool does not repair a weak key mode. Exit 3 is the stop.

## Before a GitHub upload

The sample audit in `examples/passing-audit/` contains a public key and a signature. The private key that produced it is not in this tree.

From the project directory:

```bash
find . -path './.venv' -prune -o \( -name '*.priv' -o -name 'hmac.key' -o -name '*.pem' \) -print
test ! -d workspace && echo "no workspace"
```

What good looks like: `find` prints nothing, then `no workspace`.

Do not upload `.venv/`, `workspace/`, `out/`, `WHAT-WE-BUILT.md`, or any private key. Those names are in `.gitignore`.
