# Memory

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The full list of roles it does not fill is in [getting-started.md](../getting-started.md#what-this-tool-is-not).

Think of the notes as a notebook with four trays.

The first tray is short-term memory (STM). It is the scratch pad. New notes land here unless you ask for another tray. It holds at most 100 notes.

The second tray is semantic memory. Notes here are allowed to fade when you sleep.

The third tray is the graph. It holds links between names, not paragraphs. A link has two ends, a relation, and a weight.

The fourth tray is long-term memory (LTM). Notes that matter stay here. Sleep does not throw them away.

`vesper sleep` is the command that walks the trays. `vesper remember` adds a note. `vesper link` adds a graph edge. `vesper memory export` prints the four trays as JSON and writes no file.

## Exact rules

STM cap is 100. When a 101st STM note is added, the oldest note by `(ts, id)` is dropped. STM weights are not multiplied by the hourly fade.

Semantic decay uses lambda `0.02` per hour:

```text
weight = clamp(weight * exp(-0.02 * hours))
```

`hours` is `(now - last_decay_unix) / 3600` when `last_decay_unix` is set, otherwise `(now - ts) / 3600`. If `now` equals that base time, hours are 0 and the factor is 1, so the weight does not change. If `now` is earlier than the base, the weight is left unchanged. A clock step backward does not increase a weight. After a fade, `last_decay_unix` becomes `now`.

If the state file contains `decay_lambda`, that finite number is used instead, and it must sit in `(0, 1]`. Init does not write `decay_lambda`. The default remains `0.02`.

A semantic note is dropped when `weight < 0.02` and `valence < 0.4`, unless `pinned` is true.

Graph edges do not decay in v0.1. Their weights are not multiplied by the exponential. Sleep removes an edge when `weight < 0.05`, unless `pinned` is true. Surviving edges are sorted by `src`, `dst`, `rel`, then `id`. Ends are stored with `src` and `dst` in sorted order. `src` and `dst` must differ.

Promotion runs after the drop and the prune. An STM or semantic note moves to LTM when `pinned` is true, or when:

```text
weight * valence * user_weight >= 0.45
```

`user_weight` defaults to `1.0` and must sit in `(0, 2]`. You set the initial value with `init --user-weight`.

LTM is never auto-deleted. If several LTM notes share an id, sleep keeps the one with the greater weight. If the weights are equal, it keeps the one whose SHA-256 of `seed|text|ts` is greater. `seed` defaults to `0`.

You may add a note straight to LTM with `remember --tier ltm`. Those notes follow the LTM rules. They are not faded by the semantic formula.

Text must be 1 to 4096 characters. Valence must already be inside `[0, 1]`. Weight must be finite, then it is clamped into `[0, 1]` and rounded to 10 decimal places. Ids are one path segment: `[A-Za-z0-9._-]`, length 1..128, no `..`.

## Sleep order

Given the same state, the same seed, and the same `now`, sleep is deterministic.

1. Fade each semantic weight.
2. Drop faint unpinned semantic notes.
3. Prune faint unpinned graph edges. Do not fade them.
4. Promote STM and semantic notes that are pinned or that reach `0.45`.
5. Compact LTM ids.
6. Set `last_sleep_unix` to `now`.

`--now` injects the clock as a whole number of unix seconds. Omit it to use the machine clock. When `now` equals a note's `ts`, decay is the control case: the factor is 1. A test that wants to see fade has to move `now` forward.

## What you type

```bash
vesper --workspace ./workspace remember --text "first note" --valence 0.2 --now 1700000000
vesper --workspace ./workspace link --src alpha --dst beta --rel knows --weight 0.2 --now 1700000100
vesper --workspace ./workspace sleep --now 1700000200
vesper --workspace ./workspace memory export
```

What good looks like: `remember` prints an id, `link` prints `linked`, `sleep` prints `slept`, and `memory export` prints JSON with `stm`, `semantic`, `graph`, and `ltm`.

What failure means: exit 2 for a bad number or a bad id. Exit 3 if the workspace does not exist. `--pin` on `remember` or `link` is the flag that sets `pinned` true. There is no separate pin command.
