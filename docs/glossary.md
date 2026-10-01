# Glossary

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](../getting-started.md#what-this-tool-is-not).

Each heading is one term. The first sentence says what the word means. The sentences after it state the rule this version actually enforces. Longer procedures live in the page linked from the entry.

## workspace

The workspace is the folder you name when you run `vesper init`. It holds `state.json`, the `identity/` directory, and the `forks/` directory. The program sets that one directory to mode `0700`, and it does not change the parent directories. Pass `./workspace`, or another path you will not publish. Do not pass your home directory, and do not pass the git clone itself, because init would tighten the directory you named.

## identity

The identity is the `identity/` directory inside the workspace. It holds one secret key file and `public.json`. The directory must be mode `0700`. `vesper init` refuses to reuse an identity directory that already exists. If both `edcsa-p256.priv` and `hmac.key` are present, the program refuses to load either file.

## private key

The private key is the secret that creates a signature. You do not publish it, paste it, or open it in a pager. On disk it is either `identity/edcsa-p256.priv` or `identity/hmac.key`, and the mode must be exactly `0600`. A file in any other mode is refused. The program does not change that mode and then continue. An ECDSA snapshot can still be checked from the public key stored inside the snapshot. An HMAC snapshot needs this secret.

## public key

The public key is the half you can show to someone who wants to check an ECDSA signature. `identity/public.json` is mode `0644`. For ECDSA it holds `algo`, `curve`, `kid`, and `public_key_hex`, and it does not hold a PEM block. The same public point is copied into each ECDSA snapshot, so `vesper verify` of that file does not need the workspace. An HMAC identity has no public point. Its `public.json` holds the key id only. The file mode would allow any account to read `public.json`, but the file sits inside `identity/`, which only your user can list.

## kid

A kid is the short identifier for a key. It is the first 16 hex characters of a SHA-256 hash. For ECDSA, the hash covers the uncompressed public point, which is the byte `0x04` followed by X and then Y. For HMAC, the hash covers the secret key bytes. The shortened value names the key. It is not the proof. The signature is the proof. If the kid in a snapshot does not match the public point, `verify` returns `kid` before it treats the stamp as a bad signature.

## ECDSA P-256

ECDSA P-256 is the signature algorithm this program uses when the PyPI package `ecdsa` imports. The curve is NIST P-256, also called `secp256r1`. The program hashes the canonical body with SHA-256, signs that 32-byte digest with `SigningKey.sign_digest`, DER-encodes the result with `sigencode_der`, and stores those bytes as hex. This key is not a Bitcoin key. It uses a different curve, and it only signs JSON.

## HMAC fallback

HMAC fallback is the mode used only when `import ecdsa` fails. The program writes `identity/hmac.key`, which is 32 random bytes at mode `0600`, and authenticates the canonical JSON bytes with HMAC-SHA256. It does not sign the bare digest. `vesper verify` of an HMAC snapshot loads that key from the workspace. A dry-run of init prints `hmac.key` in this mode, and `edcsa-p256.priv` when ECDSA is available.

## edcsa-p256.priv

`identity/edcsa-p256.priv` is the v0.1 filename of the ECDSA private key. The spelling `edcsa` is a misspelling of ECDSA, and that spelling is frozen for this version. Do not rename the file. Scripts, backups, and docs should use this spelling. When HMAC mode is in use, the secret file is `identity/hmac.key` instead, and `edcsa-p256.priv` is not created.

## canonical JSON

Canonical JSON is the one byte string the program hashes and signs. It is UTF-8 JSON with object keys sorted, separators `(",", ":")`, and `NaN` and `Infinity` rejected. Non-ASCII text is kept as itself. The pretty-printed file on disk is for you to read. The signature covers the canonical form of the signed body, which is every field except `signature`, and it does not cover the indentation.

## signature

A signature is the stamp stored in the `signature` field of a snapshot. ECDSA stores DER bytes as hex. HMAC stores the HMAC-SHA256 hex of the canonical body. `verify` rebuilds that body, checks the key id, and then checks the stamp. A match means the body still agrees with that key. It does not prove a legal identity, a person's name, or that the note is true.

## fork

A fork is one snapshot file, `forks/<name>.json`, at mode `0600`. It contains the notes at that moment, the parent link, the key id, and the signature. The filename stem must equal the signed `name`, so `forks/alpha.json` is valid only when the signed name is `alpha`. The audit copy keeps the name `fork_verified.json` on purpose, and verifying that path returns `name` until you copy it to a file named after the signed name. The full check order is in [forks.md](forks.md).

## parent hash

The parent hash is the hex SHA-256 of the previous snapshot's canonical signed body, stored in `parent_hash`. `parent_id` is that previous snapshot's name. A first snapshot sets both fields to JSON `null`. If one is a string and the other is `null`, `verify` returns `parent_hash`. If both are strings, the previous file must sit beside this snapshot as `<parent_id>.json`, and its content fingerprint must equal `parent_hash`.

## replay

Replay means an older snapshot is being presented as a newer one. `verify` returns `replay` when `created_unix` is earlier than the parent's, when `state_hash` is identical to the parent's, when `fork_index` in `state.json` does not match the head file, or when another snapshot in the same directory verifies and has a larger `created_unix`. An equal timestamp is allowed. A neighboring file that fails verification is ignored. A neighboring filename that is not a legal name fails the head check with `name` instead. JSON `true` is not a timestamp. A crash that writes a newer signed file before `state.json` is saved still makes `verify --head` return `replay`, and this version does not roll that back.

## schema

The schema is Uni Schema v2, the JSON shape in `fixtures/dagztagz-uni-schema-v2.json`. A notes file needs `universe_id`, `schema_version`, `character.id`, `character.callsign`, `character.straussian_level`, `memory`, and `forks`, so the program knows whose notes these are. Snapshot files use a different id, `dagztagz.uni.fork.v2`, and version `"2"`. The field rules are in [schema.md](schema.md).

## heal

Heal fills documented holes in a notes file. It may add missing `stm`, `semantic`, `graph`, and `ltm` lists, set a missing `pinned` to `false`, set a missing item `tier` to the name of the list it sits in, set a missing `user_weight` to `1.0`, set a missing `seed` to `0`, and clamp a finite weight into the range `0` through `1`. `schema heal PATH` prints the result and does not write. `schema heal PATH --write` replaces that path. `--write` keeps an existing mode that is a non-zero subset of `0644`, so a `0600` file stays `0600`. A new file, or a mode with bits outside `0644`, is written as `0644`.

## reject

Reject means the program stops and writes nothing. Heal rejects a missing or wrong-typed `universe_id`, `schema_version`, `character.id`, `character.callsign`, `character.straussian_level`, `memory` object, or `forks` list. It does not invent those fields, and it does not invent the text of a note. The names `__proto__`, `constructor`, and `prototype` are rejected anywhere in the tree. A `tier` that disagrees with the list it sits in is rejected. The command exits `2`.

## STM

STM is short-term memory, the first tray of notes. New notes go here unless you pass `--tier semantic` or `--tier ltm`. The tray holds at most 100 notes. Past that, the oldest note by `(ts, id)` is dropped. STM notes are not faded by the hourly decay formula. Sleep may move one into long-term memory.

## semantic memory

Semantic memory is the second tray. Notes here fade when you sleep. The default fade multiplies the weight by `exp(-0.02 * hours)`. A note is dropped when its weight is below `0.02` and its valence is below `0.4`, unless it is pinned. Hours are `(now - last_decay_unix) / 3600`, or `(now - ts) / 3600` when `last_decay_unix` is absent.

## graph

The graph is the third tray. An edge connects two ids with a relation word and a weight. Edges have no arrow, and `src` and `dst` are stored in sorted order. This version does not fade edge weights. Sleep removes an edge whose weight is below `0.05`, unless the edge is pinned. Graph edges use their own schema definition. They are not memory items.

## LTM

LTM is long-term memory, the fourth tray. A note moves here from STM or semantic memory when it is pinned, or when `weight * valence * user_weight` is at least `0.45`. You may also add a note directly with `remember --tier ltm`. Sleep does not delete LTM notes on its own. If two LTM notes share an id, sleep keeps the one with the larger weight. Equal weights are broken by keeping the greater SHA-256 of `seed|text|ts`.

## valence

Valence is a number from `0` to `1` on a note. You pass it as `--valence`. It says how strongly the note should count when sleep decides what to drop or promote. A value outside that range is rejected. Valence is not clamped into range, and a boolean is rejected.

## weight

Weight is a number from `0` to `1` for how strongly a note or an edge is held. You pass `--weight`, which defaults to `1.0` on `remember`. The value must be finite. It is then clamped into `0` through `1` and rounded to 10 decimal places. `user_weight` is a different number. It is a multiplier for the whole workspace, it defaults to `1.0`, and it must be greater than `0` and at most `2`.

## pin

Pin means this note or edge should be kept. `--pin` sets `pinned` to true. A pinned semantic note is not dropped for being faint. A pinned edge is not removed for a low weight. A pinned STM or semantic note is moved to LTM on sleep.

## sleep

Sleep is the command that ages the workspace. The order is fixed. It fades semantic weights, drops faint semantic notes, removes faint graph edges, promotes strong or pinned notes, compacts duplicate LTM ids, and then sets `last_sleep_unix`. The same state, the same seed, and the same `now` always produce the same result. `--now` is a whole number of unix seconds. If you omit it, the program uses the clock. The numbers are in [memory.md](memory.md).

## decay

Decay is the fade applied to semantic weights during sleep. The factor is `exp(-lambda * hours)`, and lambda is `0.02` per hour unless the state file already contains a finite `decay_lambda` in the range greater than `0` and at most `1`. When `now` equals the note's timestamp, the elapsed hours are `0` and the factor is `1`, so the weight does not change. If the clock moves backward, the weight is left as it is and does not increase. Graph edges do not decay in this version.

## audit folder

The audit folder is the directory you pass to `vesper export --audit`. The directory is mode `0700`, and each file inside it is mode `0600`. It is the packet someone else can read without your chat and without your private key. The file-by-file rules are in [audit-export.md](audit-export.md).

## plan.md

`plan.md` is the checklist the export promised to run, written the same way on every run. It also says that a passing test suite which skipped the forged sample, the moved clock, or the key-mode check does not count. Export writes this file. You do not edit it by hand to change the score.

## evidence.md

`evidence.md` is the transcript of the export. Each command is shown with its exit code, its standard output, and its standard error. The search for private-key text is recorded as an exit code. The marker text is not pasted into this file.

## critic.md

`critic.md` is the short review of that export. The headings are `BLOCKERS`, `RISKS`, `NITS`, `MISSING EVIDENCE`, `WAIVERS`, and `VERDICT`. The verdict is `ACCEPT`, `ACCEPT WITH WAIVERS`, or `REJECT`. A success verdict does not contain the letters `REJECT`.

## score.json

`score.json` is the same export result, written so a program can read it. The keys, in this order, are `task_id`, `pass`, `checks`, and `waivers`. `task_id` is always `001-heal-or-die`. `pass` is true only when every check is true and, when you run export from the terminal, the test suite exits `0`. The check names are `schema_heal_or_reject`, `forged_signature_rejected`, `parent_chain_ok`, `key_mode_enforced`, `memory_decay_ran`, `path_traversal_rejected`, and `no_secrets_in_export`. `waivers` is an empty list on a clean run.

## exit 0

Exit `0` means the command did what you asked. `verify` printed `verify ok`. `schema check` printed `schema ok`. A passing export printed `ACCEPT` or `ACCEPT WITH WAIVERS`, and then the output path.

## exit 1

Exit `1` means the command line was wrong. The program prints `usage:` and a reason. A missing required flag, an unknown command, and two different `--workspace` values on `init` are exit `1`.

## exit 2

Exit `2` means the notes, the file shape, or the signature was rejected. Schema problems, a bad valence, a bad signature, replay, and a failed export are exit `2`. The forged sample is supposed to exit `2`. That exit is the success result for that file.

## exit 3

Exit `3` means a file or a permission failed. A missing workspace, a missing state file, a key that is not mode `0600`, an identity directory that is not mode `0700`, and a refusal to overwrite an existing key are exit `3`. The program does not repair a weak key.

## mode 0600

Mode `0600` means the owner can read and write the file, and nobody else can. Private keys, `state.json`, snapshot files, and audit files use this mode. The check is exact. A file at `0644` is refused, and it is not changed to `0600` and then used.

## mode 0700

Mode `0700` means the owner can list and enter the directory, and nobody else can. The workspace root, `identity/`, `forks/`, and the audit directory use this mode. Extra bits, such as setgid, fail the exact check. `init` sets the workspace directory you named to `0700`, and it does not change parent folders.

## dry-run

Dry-run means the program prints the actions and writes nothing. It applies to `init` and `fork`. The global `--dry-run` and the command's own `--dry-run` are combined. On `init`, the printed key name is `edcsa-p256.priv` when ECDSA imports, and `hmac.key` otherwise. Other commands do not gain this behavior. Passing `--dry-run` to `remember` does not skip the write. A dry-run of `fork` still reads the existing workspace.

## unofficial

Unofficial means DagzTagz publishes this repository as a community project. It is not an xAI, SpaceXAI, or Grok product. The program does not call the Grok API. Grok Build may have drafted a patch on a person's own account. That drafting is not an endorsement.
