# Workspace

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

A workspace is the folder you name with `--workspace`. `vesper init` creates it if needed and sets **that directory** to mode `0700`. Parent directories, including your home directory, are not changed. A symlink used as the workspace root is refused.

Pass `./workspace`, or a path outside the git clone that you do not publish. Do not pass `.` and do not pass `$HOME`. Init would tighten the directory you named.

## Tree after init

ECDSA, which is the normal install:

```text
workspace/                         # mode 0700; only you can list it
├── identity/                      # mode 0700; the key directory
│   ├── edcsa-p256.priv            # mode 0600; the private key (spelled edcsa)
│   └── public.json                # mode 0644; the public key as JSON
├── state.json                     # mode 0600; the notes
└── forks/                         # mode 0700; empty until the first fork
    └── alpha.json                 # mode 0600; appears after `fork --name alpha`
```

HMAC, only when `import ecdsa` failed:

```text
workspace/
├── identity/
│   ├── hmac.key                   # mode 0600; 32 random bytes
│   └── public.json                # mode 0644; kid only, no public point
├── state.json
└── forks/
```

The program refuses to load an identity directory that contains both `edcsa-p256.priv` and `hmac.key`. Init will not overwrite an `identity/` directory that already exists.

`public.json` for ECDSA has `algo` `ecdsa-p256`, `curve` `secp256r1`, `kid`, and `public_key_hex`. It does not contain a PEM block. The private file is PEM text from the `ecdsa` library. Leave it closed.

## Who may read each file

Modes are Unix permission bits. "You" means the account that owns the files. The root account on the machine can still read them. Another ordinary account should not be able to list the directory.

| Path | Mode | Who can read it |
|------|------|-----------------|
| `workspace/` | `0700` | Only you can list or enter. |
| `identity/` | `0700` | Only you. |
| `edcsa-p256.priv` or `hmac.key` | `0600` | Only you. The check is exact. |
| `public.json` | `0644` | Any account that can reach the file can read it. |
| `state.json` | `0600` | Only you. |
| `forks/` | `0700` | Only you. |
| `forks/*.json` | `0600` | Only you. |
| an audit directory from `export --audit` | `0700` | Only you. |
| files inside that audit directory | `0600` | Only you. |

A mode with extra bits, such as setgid `2700` on a directory that must be `0700`, is refused. The program does not clear the bits and continue.

`schema heal --write` is the exception for a notes file you point it at. If that file is already mode `0600`, the healed file stays `0600`. A brand-new file, or a mode with bits outside `0644`, is written as `0644`. State saves from `remember`, `sleep`, and `fork` still write `state.json` as `0600`.

## Where not to put it

`/tmp` is a shared directory. Other accounts use it, and the system may delete it on reboot. Even with mode `0700` on your folder, a temporary cleaner can remove the key. Keep the workspace on a normal disk in your home directory, or on another path you chose for that purpose.

A USB stick formatted as FAT or exFAT does not store Unix modes. Init tries to set `0700` and `0600`. If the stick cannot hold those modes, the next load refuses the key with exit 3. Do not chmod the file on a filesystem that will forget the mode.

A cloud-sync folder may upload `edcsa-p256.priv` or `hmac.key` to someone else's servers, and the synced copy may not keep mode `0600`. The program cannot claw that copy back. `shred` on the local name does not wipe the cloud copy, and it does not wipe freed blocks on an SSD.

## Why `./workspace` is gitignored

`.gitignore` lists `workspace/`, `out/`, `*.priv`, `hmac.key`, `*.pem`, and `.env`. A normal `git add` does not pick up the notes or the key.

The ignore rule is not a lock. `git add -f workspace` would stage the key. That is why a path you will not publish is safer than a folder that sits inside the clone. The sample audit in `examples/passing-audit/` is the folder that is meant to be public, and it has a public key and a signature, not a private key.

`WHAT-WE-BUILT.md` in a local checkout is a private note. It is gitignored. Do not add it to the public repository.
