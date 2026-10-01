# vesper-runtime

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API.

**Status:** v0.1.0 experimental

## What this is

You type commands in a terminal. The program stores your notes in a folder on your computer. You can ask it to write a snapshot of that folder and stamp that snapshot with a signature. Later you can check that the file still matches the stamp, so a silent edit shows up. The program does not talk to the internet. It does not spend Grok credits.

## What you get after the first run

`vesper init` creates this folder. Each line says what the file is for.

```text
workspace/                         # the folder that holds your notes and your key
├── identity/                      # the directory that holds the key; only you can open it
│   ├── edcsa-p256.priv            # the private key; v0.1 spells this name edcsa
│   └── public.json                # the public half of the key, safe to show
├── state.json                     # your notes
└── forks/                         # empty until you write a signed snapshot
```

If Python cannot import the `ecdsa` package, the private file is `identity/hmac.key` instead. The program refuses to keep both secret files.

## Words we have to use

Longer definitions are in [docs/glossary.md](docs/glossary.md).

| Word | In one line |
|------|-------------|
| Workspace | The folder on your computer that holds the notes and the key. |
| Note | One piece of text you stored. The notes file is `state.json`. |
| Signature | A stamp on a snapshot. You use it later to see whether the file changed. |
| Fork | That snapshot file, stamp included. |
| Private key | The secret file that makes the stamp. You do not publish it. |
| Public key | The matching file someone else can use to check an ECDSA stamp. |
| Schema | The list of fields a notes file must have so the program knows whose notes they are. |
| Heal | Fill in missing lists and flags. The program will not invent who the notes belong to. |
| Sleep | Age the notes. Some fade. Important ones stay. |
| Verify | Check that a snapshot still matches its signature. |
| Audit folder | The export. It records the checks and leaves the private key out. |
| Kid | A short name for a key. It identifies the key. The signature is the check. |

## In one page

This page is the short version. Next, follow [getting-started.md](getting-started.md) through verify and the export. Then stop. The pages under `docs/` are for a person who wants the exact rules.

## Install

From Ubuntu, with Python 3.11 or newer:

```bash
git clone https://github.com/DagzTagz/vesper-runtime.git
cd vesper-runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
vesper --help
```

What good looks like: pytest prints a line that ends in `passed` and exits 0. `vesper --help` prints the command list and exits 0. Both stay on this machine.

What failure means: if `vesper` is not found, the virtual environment is not active. Run `source .venv/bin/activate` again. `which python` should point inside `.venv`. If pytest prints `failed`, stop and read the failing test name before you create a key.

## Docs map

`vesper export` writes an audit folder. That folder is a record of the checks, and it is meant to be read without the chat that produced the notes. Leave folders a skeptic can audit.

| You want to… | Read |
|--------------|------|
| Do the steps once | [getting-started.md](getting-started.md) |
| Look up a word | [docs/glossary.md](docs/glossary.md) |
| See every command | [docs/commands.md](docs/commands.md) |
| See who can read each file | [docs/workspace.md](docs/workspace.md) |
| See the notes-file rules | [docs/schema.md](docs/schema.md) |
| See how notes age | [docs/memory.md](docs/memory.md) |
| Check a signature by the rules | [docs/forks.md](docs/forks.md) |
| Read an export folder | [docs/audit-export.md](docs/audit-export.md) |
| See the failures we planned for | [docs/threat-model.md](docs/threat-model.md) |
| Get a short answer | [docs/faq.md](docs/faq.md) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |
| Run the reviewer gate | [tasks/001-heal-or-die.md](tasks/001-heal-or-die.md) |
| See what changed | [CHANGELOG.md](CHANGELOG.md) |
| See what we will not add | [ROADMAP.md](ROADMAP.md) |
| Send a patch | [CONTRIBUTING.md](CONTRIBUTING.md) |
| See rules for an agent in this tree | [AGENTS.md](AGENTS.md) |

The roles this tool does not fill are listed once in [getting-started.md](getting-started.md#what-this-tool-is-not).

## Sister repos

[dagztagz-hypothesis-engine](https://github.com/DagzTagz/dagztagz-hypothesis-engine) checks science claims.

[Dagz-Scaffold](https://github.com/DagzTagz/Dagz-Scaffold) checks whether an AI coding run left proof.

## License

Apache License 2.0. Copyright DagzTagz contributors. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

The work is provided **AS IS**. There is no warranty of fitness for a particular purpose, no warranty of merchantability, and no warranty of non-infringement.

## Attribution

DagzTagz owns this repository. Grok Build may draft a patch on your account. You review what it drafted. This program does not call the Grok API.
