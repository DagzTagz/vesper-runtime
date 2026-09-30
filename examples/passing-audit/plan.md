# Plan

Task 001-heal-or-die.

## Promised

- Heal the drifted fixture, or reject a document that has no character id.
- Sign a real fork and check the parent link.
- Reject the forged fixture in fixtures/forged-fork.json.
- Enforce mode 0600 on the private key and mode 0700 on the identity directory.
- Run semantic decay with an injected clock. now equal to ts is the control, not the proof.
- Reject path traversal in names.
- Write this folder without key material.

## Quit-early

A passing test suite that never opened the forged fixture, never moved the clock, or never checked the key mode would be quit-early. evidence.md has to show those commands.

## Result

score.json is written from the checks in this export, after evidence.md exists.
