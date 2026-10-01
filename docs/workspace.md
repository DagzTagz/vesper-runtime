# Workspace

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](../getting-started.md#what-this-tool-is-not).

The workspace is the folder you name with `--workspace`. It holds your notes and your key. `vesper init` creates that folder if it is missing, then sets **that directory** to mode `0700`. Parent folders, including your home directory, are not changed. A shortcut used as the workspace root is refused.

Pass `./workspace`, or another path you will not publish. Do not pass `.` and do not pass `$HOME`. Init would lock down the directory you named.

## What init creates

A normal install uses ECDSA. The private file is spelled `edcsa-p256.priv`. That spelling is the v0.1 name. Do not rename it.

```text
workspace/                         # mode 0700; only you can list it
├── identity/                      # mode 0700; the key directory
│   ├── edcsa-p256.priv            # mode 0600; the private key
│   └── public.json                # mode 0644; the public key
├── state.json                     # mode 0600; the notes
└── forks/                         # mode 0700; empty until the first fork
    └── alpha.json                 # mode 0600; after `fork --name alpha`
```

`public.json` then contains `algo` `ecdsa-p256`, `curve` `secp256r1`, `kid`, and `public_key_hex`. It does not contain a PEM block. The private file is PEM text from the `ecdsa` library. Leave it closed.

If `import ecdsa` fails, init writes `identity/hmac.key` instead. That file is 32 random bytes at mode `0600`. `public.json` then contains `algo` `hmac-sha256`, `hmac_kid`, and `kid`. It has no public point, and `edcsa-p256.priv` is not created.

Exactly one secret file is allowed. If both `edcsa-p256.priv` and `hmac.key` are present, the next load exits `3` with `identity directory has two key files`. Init also refuses an `identity/` directory that already exists. It does not overwrite the key.

## Who can read it

These modes are checked exactly. A directory at `2700`, or a key at `0640`, is refused. The program does not change the mode and continue. Root can still read the files. Another normal account should not be able to list the folder.

| Path | Mode | Who can open it |
|------|------|-----------------|
| `workspace/` | `0700` | Only you can list or enter. |
| `identity/` | `0700` | Only you. |
| `edcsa-p256.priv` or `hmac.key` | `0600` | Only you. The next read refuses any other mode and leaves the file as it is. |
| `public.json` | `0644` | The file itself is world-readable, but it sits in `identity/`, which only you can list. |
| `state.json` | `0600` | Only you. `remember`, `sleep`, and `fork` write it back at `0600`. |
| `forks/` | `0700` | Only you. |
| `forks/*.json` | `0600` | Only you. |
| the folder you pass to `export --audit` | `0700` | Only you. This folder is not inside the workspace unless you put it there. |
| each file in that export folder | `0600` | Only you. |

`schema heal --write` is the one write that can keep a tighter mode. If the file you name is already mode `0600`, it stays `0600`. A new file, or a mode with bits outside `0644`, is written as `0644`. Heal does not touch the private key.

## Where not to put it

| Place | Why |
|-------|-----|
| `/tmp` | Other accounts share it, and the system may delete it on reboot. Mode `0700` does not stop a temporary cleaner from removing the key. |
| A FAT or exFAT USB stick | Those filesystems do not store Unix modes. Init tries to set `0700` and `0600`. If the stick cannot keep them, the next load refuses the key and exits `3`. Do not chmod the file on a disk that will forget the mode. |
| A cloud-sync folder | The sync may upload `edcsa-p256.priv` or `hmac.key`, and the copy may not keep mode `0600`. The program cannot delete that remote copy. |

`shred -u -n 1` overwrites the named local file once and unlinks it. It does not wipe a cloud copy. On an SSD, a copy-on-write disk, or some VM disks, it may not reach the old blocks. This program does not wipe free space.

## Why `./workspace` is gitignored

`.gitignore` lists `workspace/`, `out/`, `*.priv`, `hmac.key`, `*.pem`, `.env`, and `WHAT-WE-BUILT.md`. A normal `git add` does not pick up the notes or the key.

The ignore rule is not a lock. `git add -f workspace` would stage the key. A path you will not publish is safer than a folder inside the clone. The sample in `examples/passing-audit/` is the folder meant to be public. It contains a public key and a signature, not a private key. `WHAT-WE-BUILT.md` is a local note. Leave it off the public repository.
