# Schema

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](../getting-started.md#what-this-tool-is-not).

A Uni Schema v2 document is the notes file `state.json`. The schema is the list of fields that file must have so the program knows whose notes these are. The schema itself is [fixtures/dagztagz-uni-schema-v2.json](../fixtures/dagztagz-uni-schema-v2.json). Snapshot files use a different id, `dagztagz.uni.fork.v2`, and those rules are in [forks.md](forks.md).

`vesper schema check` compares a file with that schema and does not change the file. `vesper schema heal` fills a short list of missing structural fields, then runs the same comparison. Heal does not invent who the notes belong to.

JSON `true` and `false` are not numbers and are not integers. `NaN` and `Infinity` are rejected while the file is parsed, before either command applies the schema. A path that contains `..`, or a path that is a shortcut, is rejected before the file is read.

## Fields the schema requires

The top of the file must be a JSON object. Unknown fields are kept. The names `__proto__`, `constructor`, and `prototype` are rejected anywhere in the tree.

| Field | Rule |
|-------|------|
| `universe_id` | A string with at least one character. `init` writes `uni-` plus the slug of `--callsign`. The schema does not require that prefix, and heal does not rewrite a value that is already present. |
| `schema_version` | A string with at least one character. `init` writes `"2"`. |
| `character` | An object. |
| `character.id` | A string with at least one character. `init` writes `char-` plus the same slug. Heal does not invent this field. |
| `character.callsign` | A string with at least one character. `init` stores the callsign you passed. |
| `character.straussian_level` | A finite number. `1` and `1.5` are both numbers. `init` writes `1`. Heal does not invent it and does not clamp it. |
| `memory` | An object. |
| `memory.stm`, `memory.semantic`, `memory.ltm` | Arrays of notes. |
| `memory.graph` | An array of edges. An edge is not a note. |
| `forks` | An array. It may be empty. The schema does not constrain the items inside the array. |

`user_weight` and `seed` are optional in the schema. When `user_weight` is present it must be greater than `0` and at most `2`, because the schema sets `exclusiveMinimum` to `0` and `maximum` to `2`. The checker implements that bound, so `0` is rejected and `2` is accepted. When `seed` is present it must be an integer. A boolean is not an integer.

## A note

| Field | Required by `schema check` | Rule |
|-------|----------------------------|------|
| `id` | Yes | A string with at least one character. |
| `ts` | Yes | A finite number. |
| `text` | Yes | A string. The schema does not set a minimum length, so an empty string passes `check` and `heal`. `vesper remember` still rejects empty text. |
| `valence` | Yes | A finite number from `0` through `1`, including both ends. Heal does not clamp a value outside that range. It rejects it. |
| `weight` | Yes | A finite number from `0` through `1` for `schema check`. Heal clamps a finite value into that range and rounds it to 10 decimal places, so a weight of `2` becomes `1.0` and can then pass. A missing or non-finite weight is rejected. |
| `tier` | Yes | The string `stm`, `semantic`, or `ltm`. |
| `pinned` | No | A boolean when it is present. |

`schema check` does not compare `tier` with the list that holds the note. A note in `stm` whose `tier` is `ltm` can pass `check`, because `ltm` is one of the three allowed strings. Heal rejects that note. The message is `memory item tier does not match its list`.

## An edge

| Field | Required by `schema check` | Rule |
|-------|----------------------------|------|
| `id`, `src`, `dst`, `rel` | Yes | Each one is a string with at least one character. Heal does not invent any of them. |
| `weight` | Yes | Same weight rule as a note. Heal clamps a finite value. |
| `pinned` | No | A boolean when it is present. |
| `ts` | No | A finite number when it is present. |

## What heal may add

Heal changes the document in this order, and only in these ways.

| Step | What heal does |
|------|----------------|
| 1 | Rejects a value that is not a JSON object, a non-finite number, or a reserved name. |
| 2 | Requires `universe_id`, `schema_version`, `character`, `character.id`, `character.callsign`, and `character.straussian_level` to be present and the right type. It does not fill any of them. |
| 3 | Requires `memory` to be an object and `forks` to be an array. It does not create either one. |
| 4 | Adds `stm`, `semantic`, `graph`, or `ltm` as `[]` when `memory` exists and that list is missing. A list that is present but is not an array is rejected. |
| 5 | On each note, sets a missing `tier` to the name of the list it sits in, and sets a missing `pinned` to `false`. |
| 6 | On each edge, sets a missing `pinned` to `false`. |
| 7 | Clamps each present finite weight into `0` through `1` and rounds it to 10 decimal places. |
| 8 | Sets a missing `user_weight` to `1.0`. Sets a missing `seed` to `0`. |
| 9 | Runs `schema check` on the result. If that check fails, heal fails and nothing is written. |

`vesper schema heal PATH` prints the healed JSON and does not write. The printed JSON has sorted keys and an indent of two spaces. `vesper schema heal PATH --write` replaces that file with the same JSON plus a final newline. `--write` keeps an existing mode that is a non-zero subset of `0644`, so a mode `0600` file stays `0600`. A new file, a mode of `0`, or a mode with bits outside `0644`, is written as `0644`. A shortcut is refused. If the parent directory does not exist, the command exits `3` and does not create it.

## What heal refuses to invent

Heal exits `2` and does not write when any of these are missing or the wrong type:

- `universe_id`, `schema_version`, or `character`
- `character.id`, `character.callsign`, or `character.straussian_level`
- the `memory` object or the `forks` list
- a note's `id`, `ts`, `text`, or `valence`
- an edge's `id`, `src`, `dst`, or `rel`
- a `tier` that disagrees with its list
- a non-finite weight, or a weight that is missing
- a present `user_weight` outside `(0, 2]`
- a present `seed` that is not an integer

It does not invent note text. It does not invent a character id. Unknown fields, including `builder_note`, are copied through.

## Worked example

[fixtures/drifted-state.json](../fixtures/drifted-state.json) is a notes file that fails `schema check` on purpose. It has `universe_id` `uni-drift-001`, `schema_version` `"2"`, character id `char-drift`, callsign `drift`, and `straussian_level` `1`. The `stm` list has one note, `e1`, with `text` `a drifted note`, `valence` `0.6`, and `weight` `0.8`. That note has no `tier` and no `pinned`. The `semantic`, `graph`, and `ltm` lists are absent. `forks` is `[]`. `builder_note` is `preserve me`. `user_weight` and `seed` are absent.

`pinned`, `user_weight`, and `seed` are not why `check` fails. `pinned` is optional. The file fails because `memory.semantic`, `memory.graph`, and `memory.ltm` are required and missing, and because the note has no `tier`.

```bash
vesper schema check fixtures/drifted-state.json; echo EXIT:$?
```

What good looks like: the error stream starts with `schema invalid`, one problem is printed per line, and the shell prints `EXIT:2`. `git diff -- fixtures/drifted-state.json` prints nothing.

What failure means: `EXIT:0` means this was not the drifted fixture.

Heal a copy. Do not pass the fixture itself to `--write`. The fixture has to stay drifted so `schema check` keeps exiting `2`.

```bash
mkdir -p "$HOME/vesper-heal-copy"
cp fixtures/drifted-state.json "$HOME/vesper-heal-copy/state.json"
vesper schema heal "$HOME/vesper-heal-copy/state.json" --write
```

What good looks like: the command prints `schema healed` and the copy's path. `character.id` is still `char-drift`. `builder_note` is still `preserve me`. `memory.semantic`, `memory.graph`, and `memory.ltm` are `[]`. The note's `tier` is `stm` and `pinned` is `false`. `weight` is still `0.8`. `user_weight` is `1.0` and `seed` is `0`. The file under `fixtures/` is still the original.

What failure means: exit `2`, and the copy is still byte for byte the fixture. That is what happens when an identity field is missing. A file such as `{"schema_version":"2","forks":[]}` is rejected, and `--write` does not replace it, because heal raises before the write.
