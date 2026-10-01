# Glossary

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

Each entry is the word, then the plain meaning, then the precise rule where one exists.

## workspace

The workspace is the folder you name when you run `vesper init`. It holds `state.json`, `identity/`, and `forks/`. The program sets that directory to mode `0700`. It does not change the parent directories. Pass `./workspace`, or another path you will not publish. Do not pass your home directory, and do not pass the git clone itself.

## identity

The identity is the `identity/` directory inside the workspace. It holds the secret key file and `public.json`. The directory must be mode `0700`. `vesper init` refuses to reuse an identity directory that already exists. If both `edcsa-p256.priv` and `hmac.key` are present, the program refuses to load either one.

## private key

The private key is the secret that creates a signature. You do not publish it, paste it, or open it in a pager. On disk it is either `identity/edcsa-p256.priv` or `identity/hmac.key`, mode `0600`. A file that is not exactly mode `0600` is refused. The program does not chmod it and continue. ECDSA forks can still be checked from the public key stored inside the fork. HMAC forks need this secret.

## public key

The public key is the half you can show to someone who wants to check an ECDSA signature. `identity/public.json` is mode `0644`. For ECDSA it holds `algo`, `curve`, `kid`, and `public_key_hex`. It does not hold a PEM block. The same public point is copied into each ECDSA fork, so `vesper verify` of that fork does not need the workspace. An HMAC identity has no public point. Its `public.json` holds the kid only.

## kid

A kid is a short identifier for a key. It is the first 16 hex characters of a SHA-256 hash. For ECDSA, the hash is over the uncompressed public point (`0x04` followed by X and Y). For HMAC, the hash is over the secret key bytes. The truncation names the key. It is not the proof. The signature is the proof. If the kid in a fork does not match the public point, `verify` returns `kid` before it treats the stamp as a bad signature.

## ECDSA P-256

ECDSA P-256 is the signature algorithm this program uses when the PyPI package `ecdsa` imports. The curve is NIST P-256, also called `secp256r1`. The program signs the 32-byte SHA-256 digest of the canonical JSON with `sign_digest`, DER-encodes that signature, and stores the DER bytes as hex. This key is not a Bitcoin key. It uses a different curve, and it only signs JSON.

## HMAC fallback

HMAC fallback is the mode used only when `import ecdsa` fails. The program writes `identity/hmac.key` (32 random bytes, mode `0600`) and authenticates the canonical JSON bytes with HMAC-SHA256. It does not sign a bare digest. `vesper verify` of an HMAC fork loads that key from the workspace. A dry-run of init prints `hmac.key` in this mode, and `edcsa-p256.priv` when ECDSA is available.

## edcsa-p256.priv

`identity/edcsa-p256.priv` is the v0.1 filename of the ECDSA private key. The spelling `edcsa` is a misspelling of ECDSA. It is frozen for this version. Do not rename the file in v0.1. Scripts, backups, and docs should use this spelling. The HMAC secret, when that mode is in use, is `identity/hmac.key` instead.

## canonical JSON

Canonical JSON is the one byte string the program hashes and signs. It is UTF-8 JSON with object keys sorted, with separators `(",", ":")`, and with `NaN` and `Infinity` rejected. Pretty-printed files on disk are for you to read. The signature covers the canonical form of the signed body, not the spaces in the file. The signed body is every field except `signature`.

## signature

A signature is the stamp stored in the `signature` field of a fork. ECDSA stores DER bytes as hex. HMAC stores the HMAC-SHA256 hex of the canonical body. `verify` rebuilds the canonical body, checks the kid, and checks the stamp. A match means the body still agrees with that key. It does not prove a legal identity, a person's name, or that the note is true.

## fork

A fork is a snapshot file, `forks/<name>.json`, mode `0600`. It contains the notes at that moment, the parent link, the kid, and the signature. The filename stem must equal the signed `name`. `forks/alpha.json` is valid only when the signed name is `alpha`. The audit copy `fork_verified.json` keeps that filename on purpose, so verifying that path returns reason `name` until you copy it to a file named after the signed name.

## parent hash

The parent hash is SHA-256 of the parent's canonical signed body, stored in `parent_hash`. `parent_id` is the parent's name. A first snapshot sets both to JSON `null`. If one is set and the other is not, `verify` returns `parent_hash`. If both are strings, the parent file must sit beside this fork as `<parent_id>.json`, and its content hash must equal `parent_hash`.

## replay

Replay means an old snapshot is being presented as a newer one. `verify` returns `replay` when `created_unix` is earlier than the parent's, when `state_hash` is identical to the parent's, when the workspace index does not match the head file, or when another fork in the same directory verifies and has a larger `created_unix`. A sibling that does not verify is ignored. JSON `true` is not a timestamp. A crash that writes a newer signed fork before `state.json` is saved still makes `verify --head` return `replay`. v0.1 does not roll that back.

## schema

The schema is Uni Schema v2, the JSON shape in `fixtures/dagztagz-uni-schema-v2.json`. A notes file needs `universe_id`, `schema_version`, `character` (`id`, `callsign`, `straussian_level`), `memory`, and `forks`, so the program knows whose notes these are. Fork files use a different id, `dagztagz.uni.fork.v2`, version `"2"`.

## heal

Heal fills documented holes in a notes file. It may add missing `stm`, `semantic`, `graph`, and `ltm` lists, set a missing `pinned` to `false`, set a missing item `tier` to the list name, set a missing `user_weight` to `1.0`, set a missing `seed` to `0`, and clamp a finite weight into `[0, 1]`. `schema heal PATH` prints the result. `schema heal PATH --write` replaces that path. `--write` keeps an existing mode that is a non-zero subset of `0644`, so a `0600` file stays `0600`. A new file, or a wider mode, is written as `0644`.

## reject

Reject means the program stops and writes nothing. Heal rejects a missing or wrong-typed `universe_id`, `schema_version`, `character.id`, `character.callsign`, `character.straussian_level`, `memory` object, or `forks` list. It does not invent those fields, and it does not invent note text. Reserved names `__proto__`, `constructor`, and `prototype` are rejected. A `tier` that disagrees with the list it sits in is rejected. The command exits 2.

## STM

STM is short-term memory, the first tray. New notes go here unless you pass `--tier semantic` or `--tier ltm`. The tray holds at most 100 notes. Past that, the oldest `(ts, id)` is dropped. STM notes are not faded by the hourly decay formula. Sleep may promote one into long-term memory.

## semantic memory

Semantic memory is the second tray. Notes here fade when you sleep. The default fade is `weight * exp(-0.02 * hours)`. A note is dropped when its weight is below `0.02` and its valence is below `0.4`, unless it is pinned. Hours are `(now - last_decay_unix) / 3600`, or `(now - ts) / 3600` when `last_decay_unix` is absent.

## graph

The graph is the third tray. An edge connects two ids with a relation and a weight. Edges are undirected, and `src` and `dst` are stored in sorted order. v0.1 does not fade edge weights. Sleep removes an edge whose weight is below `0.05`, unless the edge is pinned. Graph edges use their own schema definition. They are not memory items.

## LTM

LTM is long-term memory, the fourth tray. A note moves here from STM or semantic memory when it is pinned, or when `weight * valence * user_weight` is at least `0.45`. You may also `remember --tier ltm` directly. Sleep does not auto-delete LTM. If two LTM notes share an id, sleep keeps the one with the larger weight. Equal weights break the tie with the greater SHA-256 of `seed|text|ts`.

## valence

Valence is a number from 0 to 1 on a note. You pass it as `--valence`. It is how strongly the note should count when sleep decides what to drop or promote. A value outside `[0, 1]` is rejected. Valence is not clamped into range. A bool is rejected.

## weight

Weight is a number from 0 to 1 for how strongly a note or an edge is held. You pass `--weight`, which defaults to `1.0` on `remember`. The value must be finite. It is then clamped into `[0, 1]` and rounded to 10 decimal places. `user_weight` is different: it is a multiplier on the whole workspace, default `1.0`, and it must sit in `(0, 2]`.

## pin

Pin means "keep this one." `--pin` sets `pinned` to true. A pinned semantic note is not dropped for being faint. A pinned edge is not pruned. A pinned STM or semantic note is promoted to LTM on sleep.

## sleep

Sleep is the command that ages the workspace. The order is fixed: fade semantic weights, drop faint semantic notes, prune faint graph edges, promote strong or pinned notes, compact duplicate LTM ids, then set `last_sleep_unix`. The same state, seed, and `now` always produce the same result. `--now` is a whole number of unix seconds. If you omit it, the program uses the clock.

## decay

Decay is the fade applied to semantic weights during sleep. The factor is `exp(-lambda * hours)` with lambda `0.02` per hour, unless the state file already has a finite `decay_lambda` in `(0, 1]`. When `now` equals the note's timestamp, hours are 0 and the factor is 1, so the weight does not change. If the clock steps backward (`now` earlier than the last decay time), the weight is left as it is. It does not increase. Graph edges do not decay in v0.1.

## audit folder

The audit folder is the directory you pass to `vesper export --audit`. It is mode `0700`. The files inside are mode `0600`. It is the packet a stranger can read without your chat log and without your private key. See [audit-export.md](audit-export.md).

## plan.md

`plan.md` is the list of checks the export promised to run, plus a note that a green test suite which skipped those checks would be quitting early. Export writes it. You do not hand-edit it to change the score.

## evidence.md

`evidence.md` is the transcript. Each command is shown with its exit code, stdout, and stderr. The secret scan is recorded as an exit code. The marker text is not pasted into this file.

## critic.md

`critic.md` is the short review of that export. The headings are `BLOCKERS`, `RISKS`, `NITS`, `MISSING EVIDENCE`, `WAIVERS`, and `VERDICT`. The verdict is `ACCEPT`, `ACCEPT WITH WAIVERS`, or `REJECT`. A success verdict does not contain the letters `REJECT`.

## score.json

`score.json` is the machine-readable result. The keys, in this order, are `task_id`, `pass`, `checks`, and `waivers`. `task_id` is `001-heal-or-die`. `pass` is true only when every check is true and, outside pytest, the pytest child exited 0. The check names are `schema_heal_or_reject`, `forged_signature_rejected`, `parent_chain_ok`, `key_mode_enforced`, `memory_decay_ran`, `path_traversal_rejected`, and `no_secrets_in_export`. `waivers` should be `[]` on a clean run.

## exit 0

Exit 0 means the command did what it was asked. `verify` printed `verify ok`. `schema check` printed `schema ok`. A passing export printed `ACCEPT` or `ACCEPT WITH WAIVERS`, then the output path.

## exit 1

Exit 1 means the command line was wrong. The program prints `usage:` and a reason. A missing required flag, an unknown command, and two different `--workspace` values on `init` are exit 1.

## exit 2

Exit 2 means the data or the signature was rejected. Schema problems, bad valence, a bad signature, replay, and a failed export are exit 2. The forged fixture is supposed to exit 2. That exit is success for that file.

## exit 3

Exit 3 means a file or a permission failed. A missing workspace, a missing state file, a key that is not mode `0600`, an identity directory that is not mode `0700`, and a refusal to overwrite a key are exit 3. The program does not repair a weak key.

## mode 0600

Mode `0600` means the owner can read and write the file, and nobody else can. Private keys, `state.json`, fork files, and audit files use this mode. The check is exact. A file at `0644` is refused. It is not chmod'd down to `0600` and then used.

## mode 0700

Mode `0700` means the owner can list and enter the directory, and nobody else can. The workspace root, `identity/`, `forks/`, and the audit directory use this mode. Extra bits such as setgid fail the exact check. `init` sets the workspace directory you named to `0700`. It does not chmod parent folders.

## dry-run

Dry-run means print the actions and write nothing. It applies to `init` and `fork`. The global `--dry-run` and the command's own `--dry-run` are combined. On `init`, the printed key name is `edcsa-p256.priv` when ECDSA imports, and `hmac.key` otherwise. Other commands do not grow a dry-run. Passing `--dry-run` to `remember` does not skip the write.

## unofficial

Unofficial means DagzTagz publishes this repository as a community project. It is not an xAI, SpaceXAI, or Grok product. The program does not call the Grok API. Grok Build may have been used to draft a patch on a person's own account. That drafting is not an endorsement.
