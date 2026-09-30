"""Command line. Exit 0 ok, 1 usage, 2 validation or signature, 3 I/O or permissions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from vesper import __version__
from vesper.crypto import Identity
from vesper.errors import CryptoError, IOPermissionError, UsageError, ValidationError, VesperError
from vesper.export import export_audit
from vesper.fork import (
    create_fork,
    init_workspace,
    load_state,
    save_state,
    verify_fork_file,
    verify_head,
)
from vesper.memory import add_edge, new_item, remember, sleep_state
from vesper.paths import Workspace
from vesper.schema import check_document, heal, read_json, write_json_atomic


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def build_parser() -> Parser:
    parser = Parser(
        prog="vesper",
        description=f"vesper-runtime {__version__}. Local universe kernel. No network and no model API.",
    )
    parser.add_argument("--workspace", default=None, help="workspace directory (default: $VESPER_WORKSPACE or ./workspace)")
    parser.add_argument("--dry-run", action="store_true", help="print actions for init/fork and write nothing")
    sub = parser.add_subparsers(dest="command", required=True)

    schema = sub.add_parser("schema", help="check or heal a Uni Schema v2 document")
    schema_sub = schema.add_subparsers(dest="schema_cmd", required=True)
    check = schema_sub.add_parser("check")
    check.add_argument("path")
    heal_cmd = schema_sub.add_parser("heal")
    heal_cmd.add_argument("path")
    heal_cmd.add_argument("--write", action="store_true")

    init = sub.add_parser("init", help="create a workspace and a new signing key")
    init.add_argument("--workspace", dest="init_workspace")
    init.add_argument("--callsign", required=True)
    init.add_argument("--user-weight", default="1.0")
    init.add_argument("--dry-run", action="store_true", dest="command_dry_run")

    remember = sub.add_parser("remember", help="append a memory item")
    remember.add_argument("--text", required=True)
    remember.add_argument("--valence", required=True)
    remember.add_argument("--tier", default="stm", choices=["stm", "semantic", "ltm"])
    remember.add_argument("--pin", action="store_true")
    remember.add_argument("--id", default=None)
    remember.add_argument("--weight", default="1.0")
    remember.add_argument("--now", type=int, default=None)

    link = sub.add_parser("link", help="add an undirected graph edge")
    link.add_argument("--src", required=True)
    link.add_argument("--dst", required=True)
    link.add_argument("--rel", required=True)
    link.add_argument("--weight", required=True)
    link.add_argument("--pin", action="store_true")
    link.add_argument("--now", type=int, default=None)

    sleep_cmd = sub.add_parser("sleep", help="decay, prune, and promote memory")
    sleep_cmd.add_argument("--now", type=int, default=None)

    memory = sub.add_parser("memory", help="memory utilities")
    memory_sub = memory.add_subparsers(dest="memory_cmd", required=True)
    memory_sub.add_parser("export")

    fork = sub.add_parser("fork", help="sign the current state as a fork")
    fork.add_argument("--name", required=True)
    fork.add_argument("--now", type=int, default=None)
    fork.add_argument("--dry-run", action="store_true", dest="command_dry_run")

    verify = sub.add_parser("verify", help="verify a fork file or the workspace head")
    verify.add_argument("path", nargs="?")
    verify.add_argument("--head", action="store_true")
    verify.add_argument("--allow-orphan", action="store_true")

    export = sub.add_parser("export", help="write an audit bundle")
    export.add_argument("--audit", required=True)
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        _dispatch(args)
    except UsageError as exc:
        print(f"usage: {exc}", file=sys.stderr)
        return 1
    except (ValidationError, CryptoError) as exc:
        print(f"vesper: {exc}", file=sys.stderr)
        return 2
    except IOPermissionError as exc:
        print(f"vesper: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"vesper: {exc}", file=sys.stderr)
        return 3
    return 0


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(run(argv))


def _dispatch(args: argparse.Namespace) -> None:
    command = args.command
    if command == "schema":
        _schema(args)
        return
    if command == "init":
        root = _init_root(args)
        weight = _number(args.user_weight, "user-weight")
        init_workspace(root, args.callsign, dry_run=_flag(args, "dry_run"), user_weight=weight)
        if not _flag(args, "dry_run"):
            print(f"initialized {root}")
        return
    if command == "export":
        out = Path(args.audit)
        if not out.is_absolute():
            out = Path.cwd() / out
        audit = export_audit(_workspace_path(args), out)
        print(audit.verdict)
        if not audit.passed:
            raise ValidationError("audit checks failed")
        print(audit.out_dir)
        return
    if command == "verify" and not args.head:
        _verify(args, _workspace_path(args))
        return
    ws = Workspace(_workspace_path(args))
    ws.require_dir()
    if command == "remember":
        state = load_state(ws)
        item = new_item(
            text=args.text,
            valence=_number(args.valence, "valence"),
            now=_now(args.now),
            tier=args.tier,
            pinned=args.pin,
            weight=_number(args.weight, "weight"),
            item_id=args.id,
            existing=len(state["memory"][args.tier]),
        )
        remember(state, item)
        save_state(ws, state)
        print(item["id"])
        return
    if command == "link":
        state = load_state(ws)
        add_edge(
            state,
            src=args.src,
            dst=args.dst,
            rel=args.rel,
            weight=_number(args.weight, "weight"),
            now=_now(args.now),
            pinned=args.pin,
        )
        save_state(ws, state)
        print("linked")
        return
    if command == "sleep":
        state = load_state(ws)
        sleep_state(state, _now(args.now))
        save_state(ws, state)
        print("slept")
        return
    if command == "memory":
        if args.memory_cmd != "export":
            raise UsageError("unknown memory command")
        state = load_state(ws)
        text = json.dumps(state["memory"], indent=2, sort_keys=True, allow_nan=False)
        print(text)
        return
    if command == "fork":
        target = create_fork(ws.root, args.name, dry_run=_flag(args, "dry_run"), now=args.now)
        if target is not None:
            print(target)
        return
    if command == "verify":
        _verify(args, ws.root)
        return
    raise UsageError("unknown command")


def _schema(args: argparse.Namespace) -> None:
    path = Path(args.path)
    if not path.is_absolute():
        path = Path.cwd() / path
    document = read_json(path)
    if args.schema_cmd == "check":
        problems = check_document(document)
        if problems:
            print("schema invalid", file=sys.stderr)
            for problem in problems:
                print(problem, file=sys.stderr)
            raise ValidationError("schema check failed")
        print(f"schema ok {path}")
        return
    if args.schema_cmd == "heal":
        healed = heal(document)
        if args.write:
            write_json_atomic(path, healed)
            print(f"schema healed {path}")
            return
        print(json.dumps(healed, indent=2, sort_keys=True, allow_nan=False))
        return
    raise UsageError("unknown schema command")


def _verify(args: argparse.Namespace, root: Path) -> None:
    if args.head:
        result = verify_head(root, allow_orphan=args.allow_orphan)
    elif args.path:
        path = Path(args.path)
        if not path.is_absolute():
            path = Path.cwd() / path
        result = verify_fork_file(
            path,
            identity=_hmac_identity(path, root),
            allow_orphan=args.allow_orphan,
        )
    else:
        raise UsageError("verify needs a path or --head")
    if not result.ok:
        raise CryptoError(result.reason)
    print("verify ok")
    for waiver in result.waivers:
        print(f"waiver {waiver['id']}: {waiver['reason']}")


def _peek_algo(path: Path) -> str | None:
    """Read only the algo field. A bad file is left for verify to reject."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if isinstance(document, dict) and isinstance(document.get("algo"), str):
        return document["algo"]
    return None


def _hmac_identity(path: Path, root: Path) -> Identity | None:
    """HMAC forks have no public point. Load the workspace key. ECDSA does not."""
    if _peek_algo(path) != "hmac-sha256":
        return None
    from vesper.crypto import load_identity
    from vesper.paths import IDENTITY_DIRNAME

    ws = Workspace(root)
    ws.require_dir()
    return load_identity(ws.sub(IDENTITY_DIRNAME))


def _workspace_path(args: argparse.Namespace) -> Path:
    chosen = args.workspace or os.environ.get("VESPER_WORKSPACE") or str(Path.cwd() / "workspace")
    path = Path(chosen)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _init_root(args: argparse.Namespace) -> Path:
    if args.init_workspace and args.workspace and Path(args.init_workspace) != Path(args.workspace):
        raise UsageError("init --workspace does not match --workspace")
    chosen = args.init_workspace or args.workspace or os.environ.get("VESPER_WORKSPACE")
    if not chosen:
        raise UsageError("init requires --workspace")
    path = Path(chosen)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _flag(args: argparse.Namespace, name: str) -> bool:
    return bool(getattr(args, name, False) or getattr(args, "command_dry_run", False))


def _now(value: int | None) -> int:
    if value is None:
        return int(time.time())
    return value


def _number(value: str, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise UsageError(f"{label} must be a number") from exc
