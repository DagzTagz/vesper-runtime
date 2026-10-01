# Memory

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](../getting-started.md#what-this-tool-is-not).

The notes live in four lists inside `state.json`. `vesper remember` adds a note. `vesper link` adds a graph edge. `vesper sleep` ages the lists. `vesper memory export` prints the four lists as JSON and writes no file.

`sleep` is a pure function of the current state, the clock you pass, and the seed. The same three inputs always produce the same result.

## The four lists

| List | What it holds | What sleep does to it |
|------|----------------|------------------------|
| `stm` | Short-term notes. This is the default tray for `remember`. | Does not fade the weight. Drops the oldest note when the list grows past 100, and that drop happens in `remember`, not in `sleep`. May move a note to `ltm`. |
| `semantic` | Notes that are allowed to fade. You ask for this tray with `--tier semantic`. | Multiplies the weight by the hourly decay, then drops a faint unpinned note. May move a survivor to `ltm`. |
| `graph` | Links between names. A link has two ends, a relation word, and a weight. It is not a note. | Does not decay the weight. Removes an unpinned link whose weight is below `0.05`. |
| `ltm` | Long-term notes. You can add one directly with `--tier ltm`. | Does not fade or delete these notes. If two notes share an id, keeps one of them. |

## Numbers this version uses

| Name | Value | Where it is applied |
|------|--------|---------------------|
| STM cap | `100` | After a note is appended to `stm`. The note with the smallest `(ts, id)` is removed until the length is 100. |
| Decay lambda | `0.02` per hour | Semantic weights only. A finite `decay_lambda` already stored in the state replaces it, and that stored value must be greater than `0` and at most `1`. `init` does not write `decay_lambda`. |
| Semantic drop | weight `< 0.02` and valence `< 0.4` | Both tests are strict. A weight of exactly `0.02`, or a valence of exactly `0.4`, keeps the note. A pinned note is kept either way. |
| Graph prune | weight `< 0.05` | Applied after the weight is clamped. A weight of exactly `0.05` is kept. A pinned edge is kept either way. |
| LTM promotion | `weight * valence * user_weight >= 0.45` | The product is not rounded before the comparison. A pinned STM or semantic note is promoted even when the product is smaller. |
| `user_weight` | default `1.0`, range `(0, 2]` | Read at the start of sleep. A missing value becomes `1.0` and is written back onto the state. You set the first value with `init --user-weight`. |
| `seed` | default `0` | Used only to break an equal-weight LTM tie. A missing seed is treated as `0` for that comparison and is not written back. A boolean is rejected. |
| Text length | `1` to `4096` characters | Empty text is rejected. |
| Valence | `[0, 1]` | A value outside that range is rejected. It is not clamped, and it is not rounded. A boolean is rejected. |
| Weight | finite, then clamped to `[0, 1]` and rounded to 10 decimal places | `remember --weight` defaults to `1.0`. `NaN` and `Infinity` are rejected. |

`pinned` counts only when the JSON value is `true`. Another truthy value, such as `1`, is not treated as pinned.

## A note and an edge

A note is one object with `id`, `ts`, `text`, `valence`, `weight`, `tier`, and `pinned`. `tier` is `stm`, `semantic`, or `ltm`, and it must match the list that holds the note. Sleep writes `last_decay_unix` onto a semantic note when it actually decays that note.

If you omit `--id`, the id is `m-` plus the first 16 hex characters of SHA-256 over `tier|now|text|count`, where `count` is how many notes are already in that tray. An id is one segment of `[A-Za-z0-9._-]`, length 1 to 128, with no `..`. The same id cannot already exist on any note or any edge.

An edge is one object with `id`, `src`, `dst`, `rel`, `weight`, `pinned`, and `ts`. It has no text and no valence. `src` and `dst` are stored in sorted order, and they must differ. If you omit the id, it is `g-` plus the first 16 hex characters of SHA-256 over `src|dst|rel|now`, using the ends after they have been sorted.

Adding a 101st STM note deletes the oldest `(ts, id)` after the append. If you pass a `--now` earlier than the notes already in the tray, the new note can be the one that is deleted.

## Decay

For each semantic note, sleep first clamps the stored weight and checks that the valence is inside `[0, 1]`. The base time is `last_decay_unix` when that field is present, and `ts` otherwise. The base must be an integer. A boolean is rejected.

If `now` is earlier than the base, that note is left unchanged. Its weight does not increase, and `last_decay_unix` is not updated. Sleep still continues with the later steps.

If `now` is greater than or equal to the base:

```text
hours = (now - base) / 3600
weight = round(clamp(weight * exp(-lambda * hours)), 10)
last_decay_unix = now
```

When `now` equals the base, `hours` is `0` and the factor is `1`, so the weight does not change. That is the control case. A test that wants to see a smaller weight has to move `now` forward.

A weight of `1.0` held for 10 hours at lambda `0.02` becomes `0.8187307531`, because `round(exp(-0.2), 10)` is that value. Graph edges are not multiplied by this factor.

## What sleep does, in order

1. Decay each semantic weight, as specified above.
2. Drop an unpinned semantic note when its weight is strictly below `0.02` and its valence is strictly below `0.4`. This happens after decay, so a note that both fades below the line and would have scored high enough for LTM is dropped and is not promoted.
3. Clamp each edge weight. Keep the edge when it is pinned or when the clamped weight is greater than or equal to `0.05`. Sort the survivors by `src`, then `dst`, then `rel`, then `id`.
4. Walk `stm`, then `semantic`. Clamp the weight and check the valence. Move the note to `ltm` when it is pinned or when `weight * valence * user_weight` is greater than or equal to `0.45`. Set `tier` to `ltm` on the moved note. Sort the moved notes by `id`, then append them to `ltm`.
5. Compact `ltm` by id. Keep the copy with the greater weight. If the weights are equal, keep the copy whose SHA-256 hex of `seed|text|ts` is greater. Return the remaining notes sorted by id. A missing `text` or `ts` is treated as an empty string in that hash.
6. Set `last_sleep_unix` to `now`.

Direct `remember --tier ltm` does not pass through semantic decay. Those notes are not deleted by step 2. They are included in the LTM compact if a duplicate id is already present.

## Commands

```bash
vesper --workspace ./workspace remember --text "first note" --valence 0.2 --now 1700000000
vesper --workspace ./workspace link --src alpha --dst beta --rel knows --weight 0.2 --now 1700000100
vesper --workspace ./workspace sleep --now 1700000200
vesper --workspace ./workspace memory export
```

What good looks like: `remember` prints an id, `link` prints `linked`, `sleep` prints `slept`, and `memory export` prints JSON with `stm`, `semantic`, `graph`, and `ltm`. In this sample the note stays in `stm`, because `1.0 * 0.2 * 1.0` is `0.2`, which is below `0.45`. The edge stays, because its weight `0.2` is not below `0.05`. Nothing fades, because the semantic list is empty.

What failure means: exit `2` when a number, a name, or a text length is rejected. Exit `3` when the workspace does not exist. `--pin` on `remember` or `link` is the flag that sets `pinned` to true. There is no separate pin command. `--dry-run` does not skip these writes.
