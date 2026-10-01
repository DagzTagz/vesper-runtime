# Getting started

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API.

You can follow this page from install through verify and export, then stop. The exact rules live under [docs/](docs/glossary.md).

## What you will do in this guide

- Install the program and see its command list.
- Create a private folder for notes and a new key.
- Add a note, age the notes, write a signed snapshot, and check that snapshot.
- Check a sample file that is supposed to fail.
- Export a folder someone else can read without your key.
- Learn how to back up or destroy the key before you publish anything.

## Requirements

Use Ubuntu. You need Python 3.11 or newer, and git. Check the version:

```bash
python3 --version
git --version
```

What good looks like: the Python line starts with `Python 3.11` or a newer `3.`. Git prints a version.

What failure means: `python3: command not found` means the interpreter is not installed. Install it, then check the version again:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

What good looks like: `apt` finishes without an error, and `python3 --version` prints 3.11 or newer.

What failure means: `apt` asks for a password or reports a package that cannot be found. Fix that before you create a virtual environment. This program does not install system packages for you.

## Install

From the directory where you want the clone:

```bash
git clone https://github.com/DagzTagz/vesper-runtime.git
cd vesper-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
vesper --help
```

What good looks like: pytest prints a line that ends in `passed` and exits 0. `vesper --help` lists `init`, `remember`, `link`, `sleep`, `fork`, `verify`, `schema`, `memory`, and `export`, and exits 0.

What failure means: `vesper: command not found` means the virtual environment is not active. Run `source .venv/bin/activate` again. `which python` should be a path inside `.venv`. If pytest prints `failed`, stop. Do not create a key on a tree whose tests are failing.

The install does not open a network connection of its own beyond what `git` and `pip` do while you run them. Later `vesper` commands stay on this machine.

## Dry-run init

A dry-run prints the files init would write. It does not create them.

Pick a callsign. A callsign is the short name stored with your notes. `nova` is a fine example. Use letters, digits, spaces, hyphens, or underscores, 1 to 64 characters, and do not use `/` or `..`.

Name the folder `./workspace`. Init sets that directory to mode `0700`. Do not pass `$HOME`, and do not pass `.`, because the program would tighten that directory and would not touch its parents.

```bash
vesper init --workspace ./workspace --callsign nova --dry-run
test ! -e workspace && echo "no files written"
```

What good looks like: several lines that start with `dry-run: would`. On a normal install the private-key line names `identity/edcsa-p256.priv` at mode `0600`. If Python cannot import `ecdsa`, that line names `identity/hmac.key` instead. Then the shell prints `no files written`. The spelling `edcsa` in `edcsa-p256.priv` is the v0.1 filename. Leave it spelled that way.

What failure means: exit 1 and `usage:` means `--workspace` or `--callsign` was missing, or the two workspace flags disagreed. Exit 2 means the callsign has a character the program will not store, or `--user-weight` is outside `(0, 2]`.

## Real init

This step writes a key. The key stays in the folder you named.

```bash
vesper init --workspace ./workspace --callsign nova
stat -c '%a %n' workspace workspace/identity workspace/identity/* workspace/state.json workspace/forks
```

What good looks like: the first command prints `initialized` and a path, and exits 0. `stat` prints:

| Path | Mode | What it is |
|------|------|------------|
| `workspace` | `700` | Only your user can list it. |
| `workspace/identity` | `700` | The key directory. |
| `workspace/identity/edcsa-p256.priv` | `600` | The private key. v0.1 spells this `edcsa`. |
| `workspace/identity/public.json` | `644` | The public key as JSON. |
| `workspace/state.json` | `600` | The notes file. |
| `workspace/forks` | `700` | Empty until you write a snapshot. |

The callsign `nova` is stored as character id `char-nova`. The universe id is `uni-nova`. `straussian_level` is `1`. Init is the only command that sets that level.

If `ecdsa` did not import, the secret file is `workspace/identity/hmac.key` at mode `600`, and `edcsa-p256.priv` is absent. Exactly one of those secret files should exist.

What failure means: exit 3 and `identity already exists` means this folder was already initialized. Do not delete the key to retry unless you mean to destroy it. Use the backup or destroy steps at the end of this page. Exit 3 and `refusing key that is not mode 0600` means the filesystem did not keep mode `0600`. Stop. Do not chmod the file and continue.

Do not put this folder in `/tmp`. Do not put it on a USB stick that ignores Unix modes, such as a FAT or exFAT stick. Do not put it in a cloud-sync folder. Those places are explained in [docs/workspace.md](docs/workspace.md).

Do not `cat`, `less`, or screenshot `edcsa-p256.priv` or `hmac.key`.

## Remember

Remember adds a note.

Valence is a number from 0 to 1. It says how strongly the note should count later. `0.2` is an ordinary note. It stays in the short-term tray on the next sleep.

```bash
vesper --workspace ./workspace remember --text "first note" --valence 0.2
```

What good looks like: one line that looks like `m-` plus hex, and exit 0. That line is the note id.

What failure means: `workspace does not exist` and exit 3 means init has not been run on that path, or you forgot `--workspace`. Exit 2 means the text was empty, longer than 4096 characters, or the valence was outside 0 to 1.

## Sleep

Sleep ages the notes. Some fade. Important ones stay.

```bash
vesper --workspace ./workspace sleep
```

What good looks like: the word `slept`, and exit 0. The ordinary note from the last step stays in the short-term tray. A pinned note, or a note whose weight times valence times user weight reaches `0.45`, moves to long-term memory. The numbers are in [docs/memory.md](docs/memory.md).

What failure means: exit 3 means the workspace or `state.json` is missing or the key mode is wrong. Exit 2 means a stored number is not usable, such as a weight that is not finite.

## Fork

Fork writes a signed snapshot file.

```bash
vesper --workspace ./workspace fork --name alpha
stat -c '%a %n' workspace/forks/alpha.json
```

What good looks like: the path of `workspace/forks/alpha.json`, exit 0, and `stat` showing mode `600`.

What failure means: exit 2 and `fork name already exists` means you already signed `alpha`. Pick a new name, such as `beta`. A name with `..` or a slash is exit 2. A clock earlier than the parent snapshot is exit 2.

## Verify

Verify checks that the snapshot still matches its signature.

```bash
vesper --workspace ./workspace verify --head
vesper verify workspace/forks/alpha.json
```

What good looks like: each command prints `verify ok` and exits 0.

The second command does not need to load your private key when the snapshot is ECDSA. The public key is inside the file. An HMAC snapshot does need the workspace key. Pass `--workspace` for that file.

What failure means: the reason is on stderr as `vesper: <reason>`, and the exit code is 2.

| Reason | What it is telling you |
|--------|------------------------|
| `bad_signature` | The stamp does not match the canonical body. |
| `kid` | The key id does not match the public point in the file. |
| `parent_missing` | The parent file is not beside this snapshot. |
| `parent_hash` | The parent link does not match the parent file, or only one of `parent_id` and `parent_hash` is set. |
| `replay` | This file is an older snapshot presented as a newer head, or it repeats the parent's state hash. |
| `name` | The filename stem is not the signed name. |
| `canonical` | The JSON is not usable as a fork. |
| `schema_id` | The fork schema id or version is wrong. |
| `state_hash` | The notes inside the file do not match the stored hash. |
| `cycle` | The parent chain loops. |
| `no_head` | The workspace has no current snapshot yet. |

`--allow-orphan` records a waiver named `orphan-parent` when the parent file is missing. Do not use it to hide a missing parent. The check rules are in [docs/forks.md](docs/forks.md).

Verify does not prove who you are in law. It proves that this file still matches the key named inside it.

## Schema check and heal on a copy

Schema check reads a JSON file and reports missing fields. It does not rewrite the file.

```bash
vesper schema check fixtures/drifted-state.json; echo EXIT:$?
```

What good looks like for this fixture: stderr starts with `schema invalid`, and the shell prints `EXIT:2`. `fixtures/drifted-state.json` is unchanged. Exit 2 is the right result for this sample, because the semantic, graph, and long-term lists are missing, and the note has no tier.

What failure means: `EXIT:0` on this fixture means you are not checking the drifted sample. A missing path is exit 3.

Heal can fill structural holes. Run it on a copy. Do not point `--write` at the fixture.

```bash
mkdir -p "$HOME/vesper-heal-copy"
cp fixtures/drifted-state.json "$HOME/vesper-heal-copy/state.json"
vesper schema heal "$HOME/vesper-heal-copy/state.json" --write
python3 - <<'PY'
import json
from pathlib import Path
doc = json.loads((Path.home() / "vesper-heal-copy" / "state.json").read_text())
print(doc["character"]["id"])
print(doc["builder_note"])
print(sorted(doc["memory"]))
print(doc["memory"]["stm"][0]["tier"], doc["memory"]["stm"][0]["pinned"])
PY
git diff -- fixtures/drifted-state.json
```

What good looks like: `schema healed` and the copy's path. The Python lines are `char-drift`, `preserve me`, the four list names, then `stm False`. `git diff` prints nothing, so the fixture was not rewritten in place.

What failure means: exit 2 and an unchanged file. Heal will not invent `universe_id`, `schema_version`, `character.id`, `callsign`, `straussian_level`, the `memory` object, the `forks` list, or the text of a note. You can delete `$HOME/vesper-heal-copy` when you are done. It is a sample copy, not your key.

## Forged fixture

This file is a snapshot with a bad stamp. Exit 2 is success for this file.

```bash
vesper verify fixtures/forged-fork.json; echo EXIT:$?
```

What good looks like: stderr contains `vesper: bad_signature`, and the shell prints `EXIT:2`.

What failure means: `EXIT:0` would mean the program accepted a bad stamp. Stop and treat that as a bug. A reason other than `bad_signature` means the fixture was edited. The file is supposed to fail the signature check, not the filename check.

## Export an audit folder

Export writes a folder of check results. It does not copy `identity/`. On a normal run it also runs pytest, so it can take a few seconds. Do this after `verify ok`.

```bash
vesper --workspace ./workspace export --audit ./out
find out -name 'edcsa-p256.priv' -o -name 'hmac.key' -o -name 'identity'
```

What good looks like: the first lines are `ACCEPT` and the `out` path, and the exit code is 0. `out/score.json` has `"pass": true` and `"waivers": []`. The folder contains `plan.md`, `evidence.md`, `critic.md`, `score.json`, `state_hash.txt`, and `fork_verified.json`. `find` prints nothing.

What failure means: you see `REJECT`, then `vesper: audit checks failed`, and exit 2. Read `out/evidence.md` for the command that failed. `ACCEPT WITH WAIVERS` with exit 0 means the checks passed and a waiver was recorded. A clean walk should not need a waiver.

`fork_verified.json` is a copy of `forks/alpha.json`, but the filename stem is `fork_verified`, not `alpha`. `vesper verify out/fork_verified.json` returns `name`. That is the filename rule. Check `workspace/forks/alpha.json`, or copy the audit file to a name that matches the signed name. Details are in [docs/audit-export.md](docs/audit-export.md).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | The command did what you asked. |
| 1 | The command line was wrong. Stderr starts with `usage:`. |
| 2 | The notes, the schema, or the signature were rejected. |
| 3 | A file is missing, or a mode is wrong. A weak key is not repaired. |

`vesper verify fixtures/forged-fork.json` is supposed to be code 2.

## What this tool is not

You have now run the program. Read this before you treat the key as something else.

This page is not legal advice. The license is the warranty text. You are responsible for the key, the notes, and where you copy them.

vesper-runtime is a local development and provenance tool. It signs JSON on your computer. The signature check does not prove a legal identity.

It is not a wallet. It is not a money transmitter. It is not a security offering. It is not an official scientific instrument. It is not an anonymity system.

It is not an xAI product, a SpaceXAI product, or a Grok product. This runtime does not call the Grok API.

There is no HIPAA claim, no SOC 2 claim, and no certification claim. Privacy is the privacy of this Unix account and this disk.

The work is provided **AS IS**, under Apache-2.0. There is no warranty of fitness for a particular purpose, no warranty of merchantability, and no warranty of non-infringement. You use it at your own risk. The authors and DagzTagz contributors are not taking custody of a key, a file, or a decision you make with one.

The algorithms are SHA-256, HMAC-SHA256, and ECDSA P-256. There is no custom cipher. There is no unpublished algorithm. The key is not a Bitcoin key.

## Backup or destroy the key

v0.1 has no rotate command. To stop using a key, archive it or destroy the file, then init a new workspace. Do not copy the old private key into the new `identity/` directory.

ECDSA snapshots keep the public key inside the fork file. They still verify after you destroy the private key. HMAC snapshots do not. Keep `hmac.key` if you still need to verify those files.

A backup belongs outside the git clone:

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

What good looks like: the backup directory is `700`, the secret file is `600`, and `public.json` is `644`.

What failure means: a mode other than those numbers means the destination did not store Unix permissions. Pick another disk. Do not email the backup. Do not put it inside the clone.

To destroy the rehearsal key and the notes folder:

```bash
if [ -f workspace/identity/edcsa-p256.priv ]; then shred -u -n 1 workspace/identity/edcsa-p256.priv; fi
if [ -f workspace/identity/hmac.key ]; then shred -u -n 1 workspace/identity/hmac.key; fi
rm -rf workspace
test ! -d workspace && echo "workspace removed"
```

What good looks like: `workspace removed`.

What failure means: `shred` overwrites the named file once and unlinks it. On an SSD, a copy-on-write disk, or some VM disks, that overwrite may not reach the old blocks. This tool does not wipe free space. A file you already copied, including a cloud copy, is still that other copy.

If `stat` ever shows a secret file at a mode other than `600`, stop using it. Shred that file and init again on a filesystem that stores Unix modes. Do not chmod it and keep signing.

## Before a GitHub upload

The sample in `examples/passing-audit/` contains a public key and a signature. The private key that produced it is not in this tree.

From the project directory, with the virtual environment's secrets left out of the search:

```bash
find . -path './.venv' -prune -o \( -name '*.priv' -o -name 'hmac.key' -o -name '*.pem' \) -print
test ! -d workspace && echo "no workspace"
test ! -d out && echo "no out"
```

What good looks like: `find` prints nothing, then `no workspace` and `no out`.

What failure means: a printed path is a key or a PEM file. Do not commit it. If `workspace` or `out` still exists, leave them untracked. Both names are in `.gitignore`, and so is `WHAT-WE-BUILT.md`. A force-add can still publish a gitignored file. Prefer a workspace path you will not publish.

Do not upload `.venv/`. The only `.pem` you should expect on a dev machine is pip's certificate bundle inside `.venv`, and the `find` above skips that directory.

## Where to go next

Stop here if you only wanted to see a signed snapshot.

| Next question | Page |
|---------------|------|
| What a word means | [docs/glossary.md](docs/glossary.md) |
| Every command and flag | [docs/commands.md](docs/commands.md) |
| Who can read the folder | [docs/workspace.md](docs/workspace.md) |
| Why heal refused a file | [docs/schema.md](docs/schema.md) |
| How sleep decides | [docs/memory.md](docs/memory.md) |
| How verify decides | [docs/forks.md](docs/forks.md) |
| How to read an export | [docs/audit-export.md](docs/audit-export.md) |
| Which failures are in scope | [docs/threat-model.md](docs/threat-model.md) |
| Short answers | [docs/faq.md](docs/faq.md) |
| How to report a vulnerability | [SECURITY.md](SECURITY.md) |
| The reviewer gate | [tasks/001-heal-or-die.md](tasks/001-heal-or-die.md) |
