# Evidence

Commands below were executed. Exit codes are the process status.

## Command 1

```
python -m pytest -q
```

exit: 0

stdout:
```
..........................................................               [100%]
58 passed in 2.08s
```

stderr:
```

```

## Command 2

```
vesper schema check fixtures/drifted-state.json
```

exit: 2

stdout:
```

```

stderr:
```
schema invalid
$.memory.semantic: required
$.memory.graph: required
$.memory.ltm: required
$.memory.stm[0].tier: required
vesper: schema check failed
```

## Command 3

```
heal drifted fixture in a temp copy; heal a document with no character id
```

exit: 0

stdout:
```
healed=True identity_rejected=True
```

stderr:
```

```

## Command 4

```
vesper verify fixtures/forged-fork.json; echo EXIT:$?
```

exit: 0

stdout:
```
EXIT:2
```

stderr:
```
vesper: bad_signature
```

## Command 5

```
verify_fork_file(fixtures/forged-fork.json)
```

exit: 0

stdout:
```
reason=bad_signature prefix=abababab
```

stderr:
```

```

## Command 6

```
temp workspace: sign alpha then beta; lie about parent_hash; drop a parent; copy an old file onto a new name
```

exit: 0

stdout:
```
chain=True bad_parent=True missing_parent=True replay=True
```

stderr:
```

```

## Command 7

```
stat -c '%a' workspace/identity/*
```

exit: 0

stdout:
```
600
644
```

stderr:
```

```

## Command 8

```
stat -c %n %a identity/edcsa-p256.priv identity/public.json
```

exit: 0

stdout:
```
identity/edcsa-p256.priv 600
identity/public.json 644
```

stderr:
```

```

## Command 9

```
fstat identity directory; refuse a mode 0644 key without changing it
```

exit: 0

stdout:
```
directory_0700=True key_0600=True weak_refused=True
```

stderr:
```

```

## Command 10

```
sleep_state semantic weight 1.0 from ts 0 to now 36000 (lambda 0.02/hour); control now==ts
```

exit: 0

stdout:
```
before=1.0 same_clock=1.0 after=0.8187307531
```

stderr:
```

```

## Command 11

```
validate_name on traversal samples
```

exit: 0

stdout:
```
rejected=True
```

stderr:
```

```

## Secret-marker scan

secret-marker scan exit: 1; hits: 0

The scan looks for PEM-shaped fragments. Those fragments are not pasted here, so this file does not contain them.
