# Commands

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](../getting-started.md#what-this-tool-is-not).

The program is `vesper`. You type a command in the terminal. It reads or writes a folder on this computer. It does not use the network.

These are the only commands and flags. A flag you remember from an older note, and cannot find in the tables below, does not exist.

## How to read a result

The program always ends with a number called an exit code. `0` means it did the thing you asked.

| Exit code | What you see | What it means |
|-----------|--------------|---------------|
| `0` | The success line for that command, such as `verify ok` or `initialized`. | The command finished. |
| `1` | A line on the error stream that starts with `usage:`. | The command line itself is wrong. A required flag is missing, a flag is not a number, or the command name is unknown. |
| `2` | A line that starts with `vesper:`. | The notes, the file shape, or the signature was rejected. For the forged sample, this is the result you want. |
| `3` | A line that starts with `vesper:`. | A file is missing, or a permission is wrong. A private key that other people can read is not repaired. |

## Flags on every command

| Flag | What you are doing | What you pass | Success | Failure |
|------|--------------------|---------------|---------|---------|
| `--workspace` | Choosing the notes folder. | A path. If you omit it, the program uses the `VESPER_WORKSPACE` environment variable, then `./workspace`. `init` also has its own `--workspace`. If you pass both and they differ, init stops. | The command uses that folder. | Exit `1` when the two init paths disagree. Exit `3` when a later command needs the folder and it does not exist. |
| `--dry-run` | Asking `init` or `fork` to tell you what they would write, and then write nothing. | No value. You can put it before the command or after `init` or `fork`. The two places count as the same switch. | `init` or `fork` prints lines that start with `dry-run:`. No new file is created. | Other commands do not have this behavior. `remember`, `sleep`, and `link` still write if you pass `--dry-run`. |

## Every command

| Command | What you are doing | Flags that matter | Success | Failure |
|---------|--------------------|-------------------|---------|---------|
| `vesper --help` | Reading the command list. | None. | Exit `0`, and the list that includes `init`, `remember`, `link`, `sleep`, `memory`, `fork`, `verify`, `schema`, and `export`. | Exit `1` if `--help` is attached to a word the program does not know. |
| `vesper init` | Creating the notes folder and a new key. | `--workspace`, required unless `VESPER_WORKSPACE` is set. `--callsign`, required: the short name for these notes, 1 to 64 characters, no `/` and no `..`. `--user-weight`, optional, default `1.0`: a multiplier for the whole folder, greater than `0` and at most `2`. `--dry-run`. | Prints `initialized` and the path. The folder, `identity/`, and `forks/` are mode `0700` (only you can list them). The secret file is mode `0600` (only you can read it). `public.json` is mode `0644`, so the file itself is world-readable, but it sits in `identity/`, which only you can list. `state.json` is mode `0600`. | Exit `1` if `--workspace` or `--callsign` is missing, or `--user-weight` is not a number. Exit `2` if the callsign is rejected or `--user-weight` is outside that range. Exit `3` if `identity/` already exists, the folder is a shortcut, or the secret file is not mode `0600`. Dry-run writes nothing and does not print `initialized`. |
| `vesper remember` | Adding one note. | `--text`, required, 1 to 4096 characters. `--valence`, required, from `0` to `1`: how strongly this note should count later. `--tier`, optional, default `stm`: `stm` is the short-term tray, `semantic` is the tray that can fade, `ltm` is the long-term tray. `--pin` keeps this note. `--id` chooses the note's name; omit it and the program picks one. `--weight`, default `1.0`: how strongly the note is held, from `0` to `1`. `--now`, a whole number of seconds. | Prints the note id and exits `0`. A chosen id is printed as you typed it. An automatic id looks like `m-` plus hex. | Exit `3` if the folder or `state.json` is missing. Exit `2` if the text, valence, weight, id, or tray is rejected, or that id already exists. |
| `vesper link` | Connecting two notes by name. The link has no arrow. A link from A to B is the same link as B to A. | `--src`, `--dst`, `--rel`, and `--weight` are required. `--rel` is a short word for the connection, such as `knows`. `--pin` keeps the link. `--now` is a whole number of seconds. There is no `--id` flag. The program names the link. | Prints `linked` and exits `0`. The two ends are stored in alphabetical order. | Exit `2` if a name is unsafe, the two ends are the same, or the weight is not a real number. Exit `3` if the folder is missing. |
| `vesper sleep` | Aging the notes. Some fade. Important ones stay. The exact order is in [memory.md](memory.md). | `--now`, a whole number of seconds. Omit it to use the clock. | Prints `slept` and exits `0`. | Exit `2` if a stored number cannot be used. Exit `3` if the folder is missing. `--dry-run` does not skip this write. |
| `vesper fork` | Saving a signed snapshot of the notes as they are now. | `--name`, required. The snapshot file will be `forks/<name>.json`. `--now`, a whole number of seconds. `--dry-run`. | Prints the path and exits `0`. The file is mode `0600`. The first snapshot has no parent: both parent fields are JSON `null`. | Exit `2` if the name is unsafe, that name already exists, or `--now` is earlier than the previous snapshot. Dry-run prints `dry-run: would sign` and does not write the snapshot. The folder must already exist, because dry-run still reads the key and the notes. |
| `vesper verify PATH` | Checking one snapshot file against its signature. | The path. `--allow-orphan`, explained below. | Prints `verify ok` and exits `0`. A normal signature carries its public key inside the file, so this check does not need the notes folder. The backup signature, used only when the `ecdsa` package did not import, does need the folder. The program opens that secret only after it sees that the file says `hmac-sha256`. | Exit `2` and `vesper:` plus one word from the reason table below. Exit `1` if you pass neither a path nor `--head`. |
| `vesper verify --head` | Checking the snapshot your notes file calls current, then looking at the other snapshot files beside it. | `--workspace`. `--allow-orphan`. If you also pass a path, the path is ignored and `--head` is what runs. | Prints `verify ok` and exits `0`. A recorded exception is printed as `waiver <id>: <reason>`. | Exit `2`. `no_head` means you have not saved a snapshot yet. `replay` means the notes file and the snapshot disagree, or another snapshot in the folder verifies and is newer. A neighbor file that does not verify is ignored. The JSON value `true` is not a time. |
| `vesper schema check PATH` | Asking whether a notes file has the fields the program needs. | The path. | Prints `schema ok` and the path, exit `0`. The file is not changed. | Exit `2`. The error stream starts with `schema invalid`, then one problem per line, then `vesper: schema check failed`. `fixtures/drifted-state.json` is supposed to exit `2`. Exit `3` if the path cannot be read. |
| `vesper schema heal PATH` | Filling in missing lists and flags. It will not invent whose notes these are. | `--write` saves the result back to that path. Without `--write`, the filled-in text is printed and the file stays as it was. | With `--write`, prints `schema healed` and the path. A file that was mode `0600` stays `0600`. | Exit `2`, and the file unchanged, when the identity fields, the notes object, or the snapshot list cannot be filled. Do not point `--write` at `fixtures/drifted-state.json`. Copy it first. Heal does not rewrite that sample unless you pass that path. |
| `vesper memory export` | Printing the four trays of notes. | `--workspace`. | Pretty JSON on the screen, exit `0`. Nothing is written to disk. | Exit `3` if the folder or `state.json` is missing. Exit `2` if the notes are not a JSON object. |
| `vesper export --audit DIR` | Writing the audit folder described in [audit-export.md](audit-export.md). | `--audit` is required. It is the folder to create. `--workspace` selects the notes. | Prints `ACCEPT`, or `ACCEPT WITH WAIVERS`, then the folder path, exit `0`. The folder is mode `0700`. The files inside are mode `0600`. | Prints `REJECT`, then `vesper: audit checks failed`, exit `2`. From the terminal, a failing test suite also fails the score. If the test suite is already running this command, a second suite is not started. |

## Why `verify` said no

The word after `vesper:` is the reason. The exit code is `2`.

| Reason | What it is telling you |
|--------|------------------------|
| `bad_signature` | The stamp does not match the snapshot. |
| `kid` | The short key id does not match the public key inside the file. |
| `parent_missing` | The previous snapshot is not sitting next to this file. A missing file, or a shortcut used as the file, also uses this reason. |
| `parent_hash` | The link to the previous snapshot does not match that file. This is also used when one of the two parent fields is set and the other is empty. |
| `replay` | This file is an older snapshot being offered as the newer one, or it repeats the previous snapshot's notes. |
| `name` | The filename does not match the name written inside the signature. `fork_verified.json` does this on purpose. The signed name is the name to use. |
| `canonical` | The file is not usable as a snapshot. The JSON is broken, or a field has the wrong kind of value. |
| `schema_id` | The file is not the snapshot type this program signs. |
| `state_hash` | The notes inside the file do not match the fingerprint stored with them. |
| `cycle` | The chain of previous snapshots loops back on itself. |
| `no_head` | The notes file does not name a current snapshot yet. |

`verify ok` is the success line. The word `ok` is not printed as a failure reason.

## `--allow-orphan`

`--allow-orphan` is a switch on `verify` and `verify --head`.

Use it only when you already know the previous snapshot file is gone and you want that fact written down. The record id is `orphan-parent`. The text is `parent file is missing and --allow-orphan was set`.

Do not use it to hide a missing parent. If the previous file is still there, the flag does not skip the link check, the clock check, or the signature check. Export checks the current snapshot without this flag. A clean export has `"waivers": []`.

## `--now`

`--now` is accepted by `remember`, `link`, `sleep`, and `fork`. It is a whole number of seconds since 1970-01-01 UTC. `1700000000` is one such number. It is not a bare switch. If you omit it, the program uses the clock, cut down to a whole second.

The same number makes `sleep` and `fork` repeatable. Tests use it so they do not wait an hour to see a note fade.

What good looks like: the command exits `0`, and the stored time equals the number you passed.

What failure means: a value that is not a whole number is exit `1`. On `fork`, a number earlier than the previous snapshot is exit `2`, and the message is `fork clock is earlier than its parent`.

## What dry-run says about the key

```bash
vesper init --workspace ./workspace --callsign nova --dry-run
```

What good looks like: the private-file line names `identity/edcsa-p256.priv` when the `ecdsa` package imported. It names `identity/hmac.key` when that package did not import. `./workspace` still does not exist. The spelling `edcsa` is the v0.1 filename. Do not rename it.

What failure means: exit `1` if `--workspace` or `--callsign` is missing. Exit `2` if the callsign is rejected or `--user-weight` is outside its range. If you expected the `edcsa-p256.priv` line and saw `hmac.key`, the `ecdsa` package did not import. Reinstall with `pip install -e ".[dev]"` if you expected the normal signature.
