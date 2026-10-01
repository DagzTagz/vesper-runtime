# FAQ

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

## Does this call Grok?

No. `vesper` does not call the Grok API, and it does not open a network connection. If you use Grok Build to edit this repository, that session is separate, on your account.

## Does it cost money?

The program does not. `pip install`, `pytest`, and `vesper` do not bill an API. Grok Build, if you use it to edit the repo, does cost money on your account.

## Is this a wallet or a Bitcoin key?

No. The key makes P-256 document signatures over JSON. It is not a Bitcoin key. It uses a different curve, and it does not hold or send money. `verify` does not prove a legal identity.

## Can I put the workspace inside the git clone?

Technically yes, because `workspace/` is listed in `.gitignore`, so a normal `git add` skips it. A force-add can still publish it. Prefer a path you will not publish. Do not pass the clone root or your home directory to `init`. Init sets the directory you named to mode `0700`.

## Why is the key file named edcsa-p256.priv?

It is a historical typo. `edcsa` is ECDSA spelled wrong, and that spelling is the v0.1 filename. Do not rename it. If the `ecdsa` package did not import, the secret file is `identity/hmac.key` instead, and `edcsa-p256.priv` is not created.

## Why did verify exit 2 on the forged file?

That is success for that file. `fixtures/forged-fork.json` is a bad stamp. `vesper verify fixtures/forged-fork.json` is supposed to print `vesper: bad_signature` and exit 2. Exit 0 on that file would be the failure.

## Why did heal refuse my file?

Heal refuses a file that is missing identity fields. Those fields are `universe_id`, `schema_version`, `character.id`, `character.callsign`, `character.straussian_level`, the `memory` object, and the `forks` list. It also refuses the wrong type, a reserved name, a tier that disagrees with its list, or a note with no text. It does not invent those values, and it does not write the file. Copy [fixtures/drifted-state.json](../fixtures/drifted-state.json) if you want to see a heal that works. Do not point `--write` at the fixture itself.

## Do I need an API key?

No. There is no account and no token for `vesper`.

## Why does verify say `name` for `fork_verified.json`?

The audit file keeps the name `fork_verified.json`. The signed name inside the sample is `alpha`. The filename stem has to match. Copy it to `alpha.json`, or run `vesper verify` on `workspace/forks/alpha.json`. Details are in [forks.md](forks.md) and [audit-export.md](audit-export.md).

## Does shred wipe the disk?

No. `shred -u -n 1` overwrites the named file once and unlinks it. On an SSD, a copy-on-write disk, or some VM disks, that overwrite may not reach the old blocks. This tool does not wipe free space. A copy you already uploaded is still that copy.
