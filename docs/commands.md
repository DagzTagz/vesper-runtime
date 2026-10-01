# Commands

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

The program is `vesper`. Exit 0 means the command finished. Exit 1 means the command line was wrong (`usage:` on stderr). Exit 2 means the notes or the signature were rejected (`vesper:` on stderr). Exit 3 means a file or a mode failed.

`--now`, where a command has it, is a whole number of unix seconds. It is not a bare switch. If you omit it, the program uses the clock, truncated to a whole second.

There is no flag beyond the ones in this table. A flag you saw in an old note and cannot find here does not exist.

## Shared flags

| Command | What a person is doing | Important flags | Success | Failure |
|---------|------------------------|-----------------|---------|---------|
| *(global)* `--workspace` | Pointing every later command at one folder | Default is `$VESPER_WORKSPACE`, then `./workspace`. `init` also has its own `--workspace`. If both are set and they differ, init stops. | The command uses that directory. | Exit 1 when the two init paths disagree. Exit 3 when the directory is missing for a command that needs it. |
| *(global)* `--dry-run` | Asking init or fork to print actions and write nothing | Also accepted on the `init` and `fork` subcommands. The two copies are combined. Other commands ignore it and still write. | Init or fork prints `dry-run:` lines and creates no file. | Exit 1 if required flags are missing. A dry-run that names the wrong key file means the `ecdsa` import does not match what you expected. |

## Commands

| Command | What a person is doing | Important flags | Success | Failure |
|---------|------------------------|-----------------|---------|---------|
| `vesper --help` | Reading the command list | none | Exit 0 and the list of subcommands. | Exit 1 if the help flag is attached to an unknown word. |
| `vesper init` | Creating the notes folder and a new key | `--workspace` (required unless `$VESPER_WORKSPACE` is set), `--callsign` (required, 1..64 characters), `--user-weight` (default `1.0`, range `(0, 2]`), `--dry-run` | Prints `initialized` and the path. Workspace and `identity/` and `forks/` are mode `0700`. The secret file is mode `0600`. `public.json` is mode `0644`. `state.json` is mode `0600`. | Exit 1 if `--workspace` or `--callsign` is missing, or `--user-weight` is not a number. Exit 2 if the callsign is rejected or `--user-weight` is outside `(0, 2]`. Exit 3 if `identity/` already exists, the root is a symlink, or the secret file is not mode `0600`. Dry-run writes nothing and does not print `initialized`. |
| `vesper remember` | Adding one note | `--text` (required, 1..4096 characters), `--valence` (required, 0..1), `--tier` (`stm`, `semantic`, or `ltm`; default `stm`), `--pin`, `--id`, `--weight` (default `1.0`), `--now` | Prints the note id (`m-` plus hex, unless you passed `--id`) and exits 0. | Exit 3 if the workspace or `state.json` is missing. Exit 2 if the text, valence, weight, id, or tier is rejected, or the id already exists. |
| `vesper link` | Connecting two ids with an undirected edge | `--src`, `--dst`, `--rel`, `--weight` (all required), `--pin`, `--now` | Prints `linked` and exits 0. `src` and `dst` are stored in sorted order. | Exit 2 if a name is unsafe, `src` equals `dst`, or the weight is not finite. Exit 3 if the workspace is missing. There is no `--id` flag. The edge id is chosen for you. |
| `vesper sleep` | Aging the notes | `--now` | Prints `slept` and exits 0. The order is in [memory.md](memory.md). | Exit 2 if a stored number cannot be used. Exit 3 if the workspace is missing. Passing `--dry-run` does not skip the write. |
| `vesper fork` | Writing a signed snapshot of the current notes | `--name` (required), `--now`, `--dry-run` | Prints the path `forks/<name>.json` and exits 0. The file is mode `0600`. The first snapshot has `parent_id` and `parent_hash` set to JSON `null`. | Exit 2 if the name is unsafe, the name already exists, or `--now` is earlier than the parent. Dry-run prints `dry-run: would sign` and does not write the snapshot. The workspace must already exist, because dry-run still reads the key and the notes. |
| `vesper verify PATH` | Checking one snapshot file | `--allow-orphan` | Prints `verify ok` and exits 0. ECDSA files do not need the workspace. HMAC files do: the program loads the workspace key only after it sees `algo` `hmac-sha256`. | Exit 2 and `vesper:` plus a reason: `ok` is not used on failure. Reasons include `bad_signature`, `kid`, `parent_missing`, `parent_hash`, `replay`, `name`, `canonical`, `schema_id`, `state_hash`, `cycle`. Exit 1 if you pass neither a path nor `--head`. |
| `vesper verify --head` | Checking the snapshot named by `state.json`, then comparing siblings | `--workspace`, `--allow-orphan` | Prints `verify ok` and exits 0. Any waiver is printed as `waiver <id>: <reason>`. | Exit 2. `no_head` means you have not forked yet. `replay` means the index disagrees, or a sibling that itself verifies has a larger `created_unix`. A sibling that fails verify is ignored. JSON `true` is not a timestamp. |
| `vesper schema check PATH` | Asking whether a JSON file has the required fields | the path | Prints `schema ok` and the path, exit 0. The file is not modified. | Exit 2, stderr starts with `schema invalid`, then one problem per line, then `vesper: schema check failed`. `fixtures/drifted-state.json` is supposed to exit 2. Exit 3 if the path cannot be read. |
| `vesper schema heal PATH` | Filling structural holes, or writing them back | `--write` | Without `--write`, the healed JSON is printed and the file is unchanged. With `--write`, the command prints `schema healed` and the path. A `0600` file stays `0600`. | Exit 2 and the file unchanged when identity fields, `memory`, or `forks` cannot be healed. Heal does not rewrite `fixtures/drifted-state.json` unless you pass that path to `--write`. Do not do that. Copy it first. |
| `vesper memory export` | Printing the four trays as JSON | `--workspace` | Pretty JSON of `memory` on stdout, exit 0. Nothing is written to disk. | Exit 3 if the workspace or `state.json` is missing. Exit 2 if the notes are not an object. |
| `vesper export --audit DIR` | Writing the audit folder | `--audit` is required. `--workspace` selects the notes. | Prints `ACCEPT` or `ACCEPT WITH WAIVERS`, then the directory, exit 0. `score.json` has `"pass": true`. The directory is mode `0700` and the files are mode `0600`. | Prints `REJECT`, then `vesper: audit checks failed`, exit 2. Outside pytest, a failing pytest child also fails the score. Inside pytest, a second pytest is not started. |

## `--allow-orphan`

`--allow-orphan` is a switch on `verify` and `verify --head`.

Use it only when you already know the parent file is gone and you want that fact recorded. The waiver id is `orphan-parent`. The reason text is `parent file is missing and --allow-orphan was set`.

Do not use it to hide a missing parent. If the parent file is present, the flag does not skip the hash check, the clock check, or the signature check. Export calls `verify --head` without this flag. A clean export has `"waivers": []`.

## `--now`

`--now` is accepted by `remember`, `link`, `sleep`, and `fork`. It is an integer. `1700000000` means that unix second. The same numbers make sleep and fork repeatable. Tests use it so they do not wait for an hour of decay.

What good looks like: the command exits 0 and the stored `ts` or `created_unix` equals the number you passed.

What failure means: a non-integer is exit 1 (`usage:` or a number error, depending on the flag). On `fork`, a value earlier than the parent snapshot is exit 2 (`fork clock is earlier than its parent`).

## Dry-run key name

```bash
vesper init --workspace ./workspace --callsign nova --dry-run
```

What good looks like: the private-file line contains `edcsa-p256.priv` when `ecdsa` imported, and `hmac.key` when it did not. `./workspace` still does not exist.

What failure means: the line names the other file. Install the `ecdsa` extra if you expected ECDSA (`pip install -e ".[dev]"`), or accept HMAC for this machine. Do not rename `edcsa-p256.priv` so the line looks familiar.
