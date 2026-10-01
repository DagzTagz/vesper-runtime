# Disclosure bulletins

Unofficial DagzTagz project. Not an xAI, SpaceXAI, or Grok product. This runtime does not call the Grok API. The roles this tool does not fill are in [getting-started.md](getting-started.md#what-this-tool-is-not).

This file is the running record of security findings that touch vesper-runtime. A finding is a public advisory, a Dependabot alert, a private report after it is safe to summarize, or a defect we confirm in this repository.

A bulletin says what is wrong, where this program uses the affected code, what an attacker would need, and what we decided. It does not change a package by itself. How to report a new problem is in [SECURITY.md](SECURITY.md).

Newest bulletin first.

## What belongs here

Write a bulletin when any of these is true:

- A dependency has a public advisory, including one Dependabot opens and cannot upgrade away.
- A private report describes a real defect, and the private details have been removed.
- We confirm a defect in this repository, whether or not a CVE number exists.
- We change our mind about an older bulletin. Add a new dated note under that bulletin. Do not silently rewrite the original facts.

Do not use this file for ordinary bugs, style nits, or a wish for a new feature. Those can be a public issue.

Do not paste a private key, a live token, or a proof of concept that still works. Name the file and the command. Leave the secret out.

## How to add one

Copy the template. Fill every field. If you do not know a fact, write "not known". Insert the new bulletin above the older ones. Give it the next id, `DB-002`, `DB-003`, and so on.

Status is one of these words:

| Status | Meaning |
|--------|---------|
| `open` | We have not decided. |
| `accepted` | This version keeps the affected code. The reason is written in the bulletin. |
| `fixed` | A commit in this repository closes it. Name that commit. |
| `withdrawn` | The report was withdrawn, or it does not apply to this program. Say why. |

```text
### DB-NNN — short title

- Id:
- Status:
- Published:
- Updated:
- Source:
- Component:
- Versions:
- Patched versions:
- Where this program uses it:
- Plain account:
- What an attacker needs:
- What is not affected:
- Decision:
- What we did not do:
- What would close it:
- Checked against:
```

## Bulletins

### DB-001 — python-ecdsa timing leak on P-256

- **Id:** DB-001. Upstream GHSA-wj6h-64fc-37mp. CVE-2024-23342. GitHub Dependabot alert 1 on this repository.
- **Status:** `accepted` for v0.1. The Dependabot alert was still `open` on GitHub when this bulletin was written. Dismissing that alert later would clear the badge only.
- **Published:** 2024-01-22 upstream. Noted here on 2026-09-30.
- **Updated:** 2026-09-30.
- **Source:** [GitHub advisory](https://github.com/advisories/GHSA-wj6h-64fc-37mp), [python-ecdsa advisory](https://github.com/tlsfuzzer/python-ecdsa/security/advisories/GHSA-wj6h-64fc-37mp), [this repository's alert](https://github.com/DagzTagz/vesper-runtime/security/dependabot/1), [NVD CVE-2024-23342](https://nvd.nist.gov/vuln/detail/CVE-2024-23342). The library's own [SECURITY.md](https://github.com/tlsfuzzer/python-ecdsa/blob/master/SECURITY.md) says side channels are out of scope.
- **Component:** PyPI package `ecdsa` (`python-ecdsa`), ecosystem pip. This program declares it in `pyproject.toml` as `ecdsa>=0.19.1`. The import is confined to `src/vesper/crypto.py`.
- **Versions:** upstream says `>= 0`. That means every published release, including the `0.19.2` copy installed in this checkout's virtual environment on 2026-09-30.
- **Patched versions:** none. The maintainers have said they do not plan a fix.
- **Where this program uses it:** `vesper init` calls `SigningKey.generate()` on NIST P-256 (`secp256r1`) inside `generate_identity`. `vesper fork` calls `SigningKey.sign_digest()` on the 32-byte SHA-256 digest, then DER-encodes the signature and stores the hex. Both calls are the operations named in the advisory. This program does not perform ECDH. ECDH is listed upstream and is unused here.
- **Plain account:** The pure-Python signer can take a slightly different amount of time depending on the secret nonce inside a signature. Someone who can measure that time closely enough, over enough signatures, may recover the nonce and then the private key. The same class of leak is reported for key generation. Checking a signature does not use that operation.
- **What an attacker needs:** A way to time `vesper init` or `vesper fork` on the machine where the private key is loaded. This CLI does not offer signing over the network. It does not listen for requests. Another account that can only read files still cannot read a mode `0600` key. Another process that can time this process during init or fork is the case this bulletin is about. This bulletin does not claim a specific number of samples. The upstream text says timing those operations may leak the nonce.
- **What is not affected:** `vesper verify` uses `VerifyingKey` and the public point stored in the fork. Upstream says verification is unaffected. An old ECDSA snapshot can still be checked after this bulletin. The check still does not prove a legal identity. HMAC mode does not import `ecdsa`. HMAC verify still needs `identity/hmac.key`.
- **Decision:** v0.1 keeps `ecdsa>=0.19.1`. The private key file stays `identity/edcsa-p256.priv` at mode `0600`. The workspace directory you name stays mode `0700`. No package version is changed by this bulletin.
- **What we did not do:** We did not run `pip install` in the hope of a newer `ecdsa`. There is no fixed release to install. We did not remove ECDSA and leave only HMAC. A stranger can check an ECDSA snapshot from the public key inside the file. An HMAC snapshot still needs the secret, so that swap would change who can verify. We did not dismiss the GitHub alert as part of writing this page.
- **What would close it:** A later change in `crypto.py` to a P-256 implementation that is built to resist this timing leak, with the same digest, DER, and hex rules so existing forks still verify. That is a new dependency and a separate review. It is not a version bump of `ecdsa`.
- **Checked against:** `main` commit `b1bff8f687f9f50dc13e7281baa702bbe117ee11` on 2026-09-30. Installed distribution `ecdsa` `0.19.2`. Requirement line `ecdsa>=0.19.1`.
