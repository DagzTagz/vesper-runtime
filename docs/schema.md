# Schema

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

A Uni Schema v2 document is a JSON file with a fixed set of fields so the program knows whose notes these are. The file on disk in this repository is [fixtures/dagztagz-uni-schema-v2.json](../fixtures/dagztagz-uni-schema-v2.json). Fork snapshots use a different id, described in [forks.md](forks.md).

## Required fields

The top of a notes file must have:

| Field | What it is |
|-------|------------|
| `universe_id` | A non-empty string. Init writes `uni-` plus the callsign slug. |
| `schema_version` | A non-empty string. Init writes `"2"`. |
| `character.id` | A non-empty string. Init writes `char-` plus the slug. |
| `character.callsign` | A non-empty string. The name you passed to `--callsign`. |
| `character.straussian_level` | A finite number. Init writes `1`. Heal will not invent it. |
| `memory` | An object. After heal it has `stm`, `semantic`, `graph`, and `ltm` lists. |
| `forks` | A list of snapshot names. It may be empty. |

A memory item, once it is complete, has `id`, `ts`, `text`, `valence`, `weight`, and `tier`. `tier` is `stm`, `semantic`, or `ltm`, and it must match the list the item sits in. `pinned` may be absent until heal sets it.

A graph edge is a separate definition, not a memory item. It needs `id`, `src`, `dst`, `rel`, and `weight`. Heal will not invent those strings.

`user_weight`, when present, must be greater than 0 and at most 2. The schema uses `exclusiveMinimum`, and the checker implements it, so 0 is rejected. `seed`, when present, must be an integer. A JSON boolean is not an integer here.

Unknown properties are kept. The names `__proto__`, `constructor`, and `prototype` are rejected anywhere in the tree.

## What heal may add

Heal may:

- add `memory.stm`, `memory.semantic`, `memory.graph`, or `memory.ltm` as `[]` when `memory` exists and that list is missing
- set `pinned` to `false` on an item or an edge that has no `pinned`
- set an item's `tier` to the name of the list it is in, when `tier` is absent
- set `user_weight` to `1.0` when it is absent
- set `seed` to `0` when it is absent
- clamp a finite weight into `[0, 1]` and round it to 10 decimal places

`vesper schema heal PATH` prints the result and does not write. `vesper schema heal PATH --write` replaces that file. `--write` keeps a mode that is already a non-zero subset of `0644`. A `0600` file stays `0600`. A new file is `0644`.

## What heal must refuse to invent

Heal exits 2 and does not write when any of these are missing or the wrong type:

- `universe_id`
- `schema_version`
- `character`, `character.id`, `character.callsign`, or `character.straussian_level`
- the `memory` object
- the `forks` list
- an item's `id`, `ts`, `text`, or `valence`
- an edge's `id`, `src`, `dst`, or `rel`
- a `tier` that disagrees with its list
- a non-finite weight
- a `user_weight` outside `(0, 2]`
- a `seed` that is present and not an integer

It does not invent note text. It does not invent a character id to fill a hole.

## Worked example

[fixtures/drifted-state.json](../fixtures/drifted-state.json) is a notes file on purpose. It has `universe_id` `uni-drift-001`, `schema_version` `"2"`, character id `char-drift`, callsign `drift`, and `straussian_level` `1`. The short-term list has one note, `e1`, with no `tier` and no `pinned`. The semantic, graph, and long-term lists are absent. `forks` is `[]`. `builder_note` is `preserve me`.

Check it. The command must fail, and the fixture must stay as it is.

```bash
vesper schema check fixtures/drifted-state.json; echo EXIT:$?
```

What good looks like: stderr starts with `schema invalid`, and the shell prints `EXIT:2`. `git diff -- fixtures/drifted-state.json` prints nothing.

What failure means: `EXIT:0` means this was not the drifted fixture.

Heal a copy:

```bash
mkdir -p "$HOME/vesper-heal-copy"
cp fixtures/drifted-state.json "$HOME/vesper-heal-copy/state.json"
vesper schema heal "$HOME/vesper-heal-copy/state.json" --write
```

What good looks like: `schema healed` and the copy's path. `character.id` is still `char-drift`. `builder_note` is still `preserve me`. `memory.semantic`, `memory.graph`, and `memory.ltm` are `[]`. The note's `tier` is `stm` and `pinned` is `false`. `user_weight` is `1.0` and `seed` is `0`. The file under `fixtures/` is still the original.

What failure means: exit 2 and a copy that still matches the fixture byte for byte. That happens when the identity fields are missing. A file like `{"schema_version":"2","forks":[]}` is rejected, and `--write` does not replace it, because heal raises before the write.

Do not pass `fixtures/drifted-state.json` to `--write`. The fixture has to stay drifted so `schema check` keeps exiting 2.
