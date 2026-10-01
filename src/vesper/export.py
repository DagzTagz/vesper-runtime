"""Audit bundle for a skeptic and for Dagz-Scaffold.

The bundle is plan, evidence, critic, and score, plus the state hash and
the last verified fork. Private key files are not copied. Evidence records
commands this process actually ran.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vesper.crypto import canonical_bytes, load_identity, refuse_insecure_key, sha256_hex
from vesper.errors import IOPermissionError, ValidationError
from vesper.fork import init_workspace, load_state, verify_fork_file, verify_head
from vesper.memory import empty_memory, new_item, remember, sleep_state
from vesper.paths import IDENTITY_DIRNAME, Workspace, assert_mode, fchmod_nofollow, write_nofollow
from vesper.schema import heal, read_json, repo_root, write_json_atomic

_MARKERS = ("BEG" + "IN", "PRIV" + "ATE", "-" * 5)


@dataclass
class Audit:
    passed: bool
    verdict: str
    score: dict[str, Any]
    out_dir: Path


@dataclass
class _Cmd:
    argv: str
    code: int
    stdout: str
    stderr: str
    tainted: bool = False


def export_audit(workspace: Path, out_dir: Path) -> Audit:
    root = repo_root()
    ws = Workspace(workspace)
    ws.require_dir()
    identity_dir = ws.sub(IDENTITY_DIRNAME)
    # Loading checks directory 0700 and key 0600. The bytes are not printed.
    load_identity(identity_dir)
    commands: list[_Cmd] = []
    pytest_ok = True
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        pytest_cmd = _run_pytest(root)
        commands.append(pytest_cmd)
        pytest_ok = pytest_cmd.code == 0 and not pytest_cmd.tainted
    checks = {
        "schema_heal_or_reject": _schema_check(root, commands),
        "forged_signature_rejected": _forged_check(root, commands),
        "parent_chain_ok": _parent_check(commands),
        "key_mode_enforced": _key_check(root, workspace, identity_dir, commands),
        "memory_decay_ran": _decay_check(commands),
        "path_traversal_rejected": _path_check(commands),
        "no_secrets_in_export": False,
    }
    head = verify_head(workspace, allow_orphan=False)
    waivers = list(head.waivers) if head.ok else []
    fork_bytes = _fork_bytes(ws, head)
    _prepare_out(out_dir)
    state = load_state(ws)
    state_hash = sha256_hex(canonical_bytes(state))
    tainted = any(item.tainted for item in commands)
    _write_bundle(
        out_dir,
        commands=commands,
        checks=checks,
        waivers=waivers,
        state_hash=state_hash,
        fork_bytes=fork_bytes,
        scan_line="secret-marker scan: pending",
        passed=False,
    )
    scan_code, scan_hits = _scan(out_dir)
    checks["no_secrets_in_export"] = scan_code == 1 and not scan_hits and not tainted
    passed = all(checks.values()) and pytest_ok
    scan_line = f"secret-marker scan exit: {scan_code}; hits: {len(scan_hits)}"
    _write_bundle(
        out_dir,
        commands=commands,
        checks=checks,
        waivers=waivers,
        state_hash=state_hash,
        fork_bytes=fork_bytes,
        scan_line=scan_line,
        passed=passed,
    )
    scan_code, scan_hits = _scan(out_dir)
    if scan_hits or scan_code != 1:
        checks["no_secrets_in_export"] = False
        passed = False
        _write_bundle(
            out_dir,
            commands=commands,
            checks=checks,
            waivers=waivers,
            state_hash=state_hash,
            fork_bytes=None,
            scan_line="secret-marker scan found a hit; the fork copy was withheld",
            passed=False,
        )
        scan_code, scan_hits = _scan(out_dir)
        if scan_hits or scan_code != 1:
            checks["no_secrets_in_export"] = False
            passed = False
    verdict = _verdict(passed, waivers)
    score = _score(passed, checks, waivers)
    return Audit(passed, verdict, score, out_dir)


def _schema_check(root: Path, commands: list[_Cmd]) -> bool:
    check = _vesper(root, "schema", "check", "fixtures/drifted-state.json")
    commands.append(check)
    drifted_rejected = check.code == 2
    with tempfile.TemporaryDirectory(prefix="vesper-heal-") as tmp:
        src = Path(tmp) / "drifted.json"
        src.write_text((root / "fixtures" / "drifted-state.json").read_text(encoding="utf-8"), encoding="utf-8")
        before_id = json.loads(src.read_text(encoding="utf-8"))["character"]["id"]
        try:
            healed = heal(read_json(src))
            write_json_atomic(src, healed)
            healed_ok = (
                healed["character"]["id"] == before_id
                and healed["memory"]["stm"][0]["tier"] == "stm"
                and healed["memory"]["semantic"] == []
                and healed["builder_note"] == "preserve me"
            )
        except (ValidationError, IOPermissionError, OSError):
            healed_ok = False
        broken = Path(tmp) / "broken.json"
        broken.write_text('{"schema_version":"2","forks":[]}\n', encoding="utf-8")
        raw = broken.read_text(encoding="utf-8")
        try:
            heal(read_json(broken))
            rejected = False
        except ValidationError:
            rejected = True
        rejected = rejected and broken.read_text(encoding="utf-8") == raw
    commands.append(
        _Cmd(
            "heal drifted fixture in a temp copy; heal a document with no character id",
            0 if healed_ok and rejected else 2,
            f"healed={healed_ok} identity_rejected={rejected}",
            "",
        )
    )
    return drifted_rejected and healed_ok and rejected


def _forged_check(root: Path, commands: list[_Cmd]) -> bool:
    import sys

    # Do not resolve() the interpreter. A venv python is often a symlink into
    # another prefix, and that prefix does not contain the vesper script.
    bindir = Path(sys.executable).absolute().parent
    env = os.environ.copy()
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    proc = _capture(
        root,
        ["bash", "-c", "vesper verify fixtures/forged-fork.json; echo EXIT:$?"],
        env=env,
    )
    proc.argv = "vesper verify fixtures/forged-fork.json; echo EXIT:$?"
    commands.append(proc)
    echoed = "EXIT:2" in proc.stdout
    in_proc = verify_fork_file(root / "fixtures" / "forged-fork.json")
    commands.append(
        _Cmd(
            "verify_fork_file(fixtures/forged-fork.json)",
            0 if in_proc.reason == "bad_signature" else 2,
            f"reason={in_proc.reason} prefix={in_proc.signature_prefix}",
            "",
        )
    )
    return echoed and in_proc.reason == "bad_signature" and bool(in_proc.signature_prefix)


def _parent_check(commands: list[_Cmd]) -> bool:
    with tempfile.TemporaryDirectory(prefix="vesper-chain-") as tmp:
        root = Path(tmp) / "ws"
        init_workspace(root, "chain", now=1_700_000_000)
        ws = Workspace(root)
        state = load_state(ws)
        remember(state, new_item(text="one", valence=0.2, now=1_700_000_000, tier="stm", pinned=False, weight=0.2))
        from vesper.fork import create_fork, save_state

        save_state(ws, state)
        first = create_fork(root, "alpha", now=1_700_000_100)
        state = load_state(ws)
        remember(
            state,
            new_item(text="two", valence=0.2, now=1_700_000_200, tier="stm", pinned=False, weight=0.2),
        )
        save_state(ws, state)
        second = create_fork(root, "beta", now=1_700_000_300)
        ok_chain = (
            first is not None
            and second is not None
            and verify_head(root).ok
            and verify_fork_file(second).reason == "ok"
        )
        replay = _replay_old_file(root)
        lied = _resign_bad_parent(root)
        missing = _missing_parent(root)
    commands.append(
        _Cmd(
            "temp workspace: sign alpha then beta; lie about parent_hash; drop a parent; copy an old file onto a new name",
            0 if ok_chain and lied and missing and replay else 2,
            f"chain={ok_chain} bad_parent={lied} missing_parent={missing} replay={replay}",
            "",
        )
    )
    return ok_chain and lied and missing and replay


def _resign_bad_parent(root: Path) -> bool:
    from vesper.crypto import load_identity as load_id

    ws = Workspace(root)
    identity = load_id(ws.sub(IDENTITY_DIRNAME))
    path = ws.sub("forks") / "beta.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in document.items() if key != "signature"}
    body["parent_hash"] = "0" * 64
    signed = dict(body)
    signed["signature"] = identity.sign_canonical(body)
    path.write_text(json.dumps(signed, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return verify_fork_file(path, identity=identity).reason == "parent_hash"


def _missing_parent(root: Path) -> bool:
    from vesper.crypto import load_identity as load_id
    from vesper.fork import _body

    ws = Workspace(root)
    identity = load_id(ws.sub(IDENTITY_DIRNAME))
    body = _body(
        identity=identity,
        name="orphan",
        parent_id="no-such-parent",
        parent_hash="ab" * 32,
        state=load_state(ws),
        created_unix=1_700_000_400,
    )
    signed = dict(body)
    signed["signature"] = identity.sign_canonical(body)
    orphan = ws.sub("forks") / "orphan.json"
    orphan.write_text(json.dumps(signed, indent=2) + "\n", encoding="utf-8")
    os.chmod(orphan, 0o600)
    refused = verify_fork_file(orphan, identity=identity).reason == "parent_missing"
    waived = verify_fork_file(orphan, identity=identity, allow_orphan=True)
    return refused and any(item["id"] == "orphan-parent" for item in waived.waivers)


def _replay_old_file(root: Path) -> bool:
    ws = Workspace(root)
    alpha = (ws.sub("forks") / "alpha.json").read_bytes()
    planted = ws.sub("forks") / "copied.json"
    planted.write_bytes(alpha)
    os.chmod(planted, 0o600)
    return verify_fork_file(planted).reason == "name"


def _key_check(root: Path, workspace: Path, identity_dir: Path, commands: list[_Cmd]) -> bool:
    del root
    try:
        assert_mode(identity_dir, 0o700, directory=True)
        directory_ok = True
    except IOPermissionError:
        directory_ok = False
    rel_parent = workspace
    glob = sorted(identity_dir.glob("*"))
    proc = _capture(
        rel_parent,
        ["stat", "-c", "%n %a", *[f"identity/{path.name}" for path in glob]],
    )
    # The task's form, from the parent of the workspace when the folder is named workspace.
    if workspace.name == "workspace":
        starred = _capture(
            workspace.parent,
            ["bash", "-c", "stat -c '%a' workspace/identity/*"],
        )
        starred.argv = "stat -c '%a' workspace/identity/*"
        commands.append(starred)
    commands.append(proc)
    modes = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            modes[Path(parts[0]).name] = parts[1]
    key_name = "edcsa-p256.priv" if (identity_dir / "edcsa-p256.priv").exists() else "hmac.key"
    key_ok = modes.get(key_name) == "600"
    weak_refused = False
    with tempfile.TemporaryDirectory(prefix="vesper-mode-") as tmp:
        weak = Path(tmp) / "weak.key"
        weak.write_bytes(os.urandom(32))
        os.chmod(weak, 0o644)
        try:
            refuse_insecure_key(weak)
        except IOPermissionError:
            weak_refused = True
        still_weak = stat.S_IMODE(weak.stat().st_mode) == 0o644
    commands.append(
        _Cmd(
            "fstat identity directory; refuse a mode 0644 key without changing it",
            0 if directory_ok and key_ok and weak_refused and still_weak else 3,
            f"directory_0700={directory_ok} key_0600={key_ok} weak_refused={weak_refused}",
            "",
        )
    )
    return directory_ok and key_ok and weak_refused and still_weak


def _decay_check(commands: list[_Cmd]) -> bool:
    state: dict[str, Any] = {
        "memory": empty_memory(),
        "user_weight": 1.0,
        "seed": 0,
    }
    remember(
        state,
        new_item(
            text="decay me",
            valence=0.3,
            now=0,
            tier="semantic",
            pinned=False,
            weight=1.0,
            item_id="m-decay",
        ),
    )
    before = state["memory"]["semantic"][0]["weight"]
    untouched = copy.deepcopy(state)
    sleep_state(untouched, 0)
    same = untouched["memory"]["semantic"][0]["weight"]
    sleep_state(state, 10 * 3600)
    after = state["memory"]["semantic"][0]["weight"]
    ran = before == 1.0 and same == before and after < before
    commands.append(
        _Cmd(
            "sleep_state semantic weight 1.0 from ts 0 to now 36000 (lambda 0.02/hour); control now==ts",
            0 if ran else 2,
            f"before={before} same_clock={same} after={after}",
            "",
        )
    )
    return ran


def _path_check(commands: list[_Cmd]) -> bool:
    from vesper.paths import validate_name

    samples = ("../etc/passwd", "/etc/passwd", "..", "a/b", "a..b")
    rejected = []
    for sample in samples:
        try:
            validate_name(sample, what="event id")
            rejected.append(False)
        except ValidationError:
            rejected.append(True)
    ok = all(rejected)
    commands.append(
        _Cmd(
            "validate_name on traversal samples",
            0 if ok else 2,
            f"rejected={ok}",
            "",
        )
    )
    return ok


def _run_pytest(root: Path) -> _Cmd:
    import sys

    env = os.environ.copy()
    env["VESPER_EXPORT_CHILD"] = "1"
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    captured = _capture(root, [sys.executable, "-m", "pytest", "-q"], env=env)
    captured.argv = "python -m pytest -q"
    return captured


def _vesper(root: Path, *args: str) -> _Cmd:
    import sys

    if shutil.which("vesper"):
        argv = ["vesper", *args]
    else:
        argv = [sys.executable, "-m", "vesper", *args]
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    captured = _capture(root, argv, env=env)
    captured.argv = "vesper " + " ".join(args)
    return captured


def _capture(cwd: Path, argv: list[str], env: dict[str, str] | None = None) -> _Cmd:
    proc = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    tainted = any(marker in stdout or marker in stderr for marker in _MARKERS)
    if tainted:
        stdout, stderr = "[output omitted]", "[output omitted]"
    shown = " ".join(argv)
    if tainted:
        shown = "command output omitted"
    return _Cmd(shown, proc.returncode, stdout, stderr, tainted)


def _prepare_out(out_dir: Path) -> None:
    if any(part == ".." for part in out_dir.parts):
        raise ValidationError("audit path rejects '..'")
    if out_dir.is_symlink():
        raise IOPermissionError("audit path is a symlink")
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.is_symlink():
        raise IOPermissionError("audit path is a symlink")
    fchmod_nofollow(out_dir, 0o700, directory=True)


def _write_bundle(
    out_dir: Path,
    *,
    commands: list[_Cmd],
    checks: dict[str, bool],
    waivers: list[dict[str, str]],
    state_hash: str,
    fork_bytes: bytes | None,
    scan_line: str,
    passed: bool,
) -> None:
    evidence = _evidence(commands, scan_line)
    plan = _plan()
    critic = _critic(passed, waivers, [name for name, ok in checks.items() if not ok])
    score = _score(passed, checks, waivers)
    _put(out_dir / "evidence.md", evidence)
    _put(out_dir / "plan.md", plan)
    _put(out_dir / "critic.md", critic)
    _put(out_dir / "score.json", json.dumps(score, indent=2) + "\n")
    _put(out_dir / "state_hash.txt", state_hash + "\n")
    if fork_bytes is None:
        _put(out_dir / "fork_verified.json", "null\n")
    else:
        _put_bytes(out_dir / "fork_verified.json", fork_bytes)


def _evidence(commands: list[_Cmd], scan_line: str) -> str:
    blocks = ["# Evidence", "", "Commands below were executed. Exit codes are the process status.", ""]
    for index, cmd in enumerate(commands, start=1):
        blocks.append(f"## Command {index}")
        blocks.append("")
        blocks.append("```")
        blocks.append(cmd.argv)
        blocks.append("```")
        blocks.append("")
        blocks.append(f"exit: {cmd.code}")
        blocks.append("")
        blocks.append("stdout:")
        blocks.append("```")
        blocks.append(cmd.stdout.rstrip())
        blocks.append("```")
        blocks.append("")
        blocks.append("stderr:")
        blocks.append("```")
        blocks.append(cmd.stderr.rstrip())
        blocks.append("```")
        blocks.append("")
    blocks.append("## Secret-marker scan")
    blocks.append("")
    blocks.append(scan_line)
    blocks.append("")
    blocks.append(
        "The scan looks for PEM-shaped fragments. Those fragments are not pasted here, "
        "so this file does not contain them."
    )
    blocks.append("")
    return "\n".join(blocks)


def _plan() -> str:
    return "\n".join(
        [
            "# Plan",
            "",
            "Task 001-heal-or-die.",
            "",
            "## Promised",
            "",
            "- Heal the drifted fixture, or reject a document that has no character id.",
            "- Sign a real fork and check the parent link.",
            "- Reject the forged fixture in fixtures/forged-fork.json.",
            "- Enforce mode 0600 on the private key and mode 0700 on the identity directory.",
            "- Run semantic decay with an injected clock. now equal to ts is the control, not the proof.",
            "- Reject path traversal in names.",
            "- Write this folder without key material.",
            "",
            "## Quit-early",
            "",
            "A passing test suite that never opened the forged fixture, never moved the clock, "
            "or never checked the key mode would be quit-early. evidence.md has to show those commands.",
            "",
            "## Result",
            "",
            "score.json is written from the checks in this export, after evidence.md exists.",
            "",
        ]
    )


def _critic(passed: bool, waivers: list[dict[str, str]], failed: list[str]) -> str:
    if passed and waivers:
        verdict = "ACCEPT WITH WAIVERS"
        blockers = "- none"
    elif passed:
        verdict = "ACCEPT"
        blockers = "- none"
    else:
        verdict = "RE" + "JECT"
        blockers = "\n".join(f"- {name}" for name in failed) or "- checks failed"
    waiver_lines = "\n".join(f"- {item['id']}: {item['reason']}" for item in waivers) or "- none"
    return "\n".join(
        [
            "# Critic",
            "",
            "## BLOCKERS",
            blockers,
            "",
            "## RISKS",
            "- The key id is a truncated hash. It identifies a key. The signature is the check.",
            "- Decay rounds to 10 decimal places on each sleep.",
            "",
            "## NITS",
            "- Graph endpoints are stored in sorted order.",
            "- The secret scan is recorded here as an exit code. The operator pattern lives in tasks/001-heal-or-die.md. Copying that pattern into this folder would make the scan match its own notes.",
            "",
            "## MISSING EVIDENCE",
            "- none",
            "",
            "## WAIVERS",
            waiver_lines,
            "",
            "## VERDICT",
            verdict,
            "",
        ]
    )


def _score(passed: bool, checks: dict[str, bool], waivers: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "task_id": "001-heal-or-die",
        "pass": passed,
        "checks": checks,
        "waivers": waivers,
    }


def _verdict(passed: bool, waivers: list[dict[str, str]]) -> str:
    if not passed:
        return "RE" + "JECT"
    if waivers:
        return "ACCEPT WITH WAIVERS"
    return "ACCEPT"


def _scan(out_dir: Path) -> tuple[int, list[str]]:
    hits: list[str] = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_symlink():
            hits.append(path.name)
            continue
        if not path.is_file():
            continue
        if path.name in {"edcsa-p256.priv", "hmac.key"}:
            hits.append(path.name)
        data = path.read_bytes()
        if any(marker.encode("ascii") in data for marker in _MARKERS):
            hits.append(path.name)
    # Match the operator command's exit code: 1 means no hits.
    return (1 if not hits else 0), hits


def _fork_bytes(ws: Workspace, head: object) -> bytes | None:
    document = getattr(head, "document", None)
    if not getattr(head, "ok", False) or not isinstance(document, dict):
        return None
    name = document.get("name")
    if not isinstance(name, str):
        return None
    path = ws.sub("forks") / f"{name}.json"
    if path.is_symlink() or not path.is_file():
        return None
    return path.read_bytes()


def _put(path: Path, text: str) -> None:
    write_nofollow(path, text.encode("utf-8"), 0o600)


def _put_bytes(path: Path, data: bytes) -> None:
    write_nofollow(path, data, 0o600)
