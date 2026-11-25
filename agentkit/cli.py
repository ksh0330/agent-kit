"""Command line: python -m agentkit ..."""

from __future__ import annotations

import argparse
import sys

from agentkit import __version__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agentkit", description="agent-kit command line")
    parser.add_argument("--version", action="version", version=f"agentkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    guard = sub.add_parser("guard", help="commit-guard: block unwanted authors and attribution text")
    gsub = guard.add_subparsers(dest="action", required=True)
    install = gsub.add_parser("install", help="install commit-msg and pre-push hooks into .git/hooks")
    install.add_argument("--force", action="store_true", help="install even when core.hooksPath is set")
    install.add_argument("--no-config", action="store_true", help="do not create .commit-guard.json")
    check = gsub.add_parser("check", help="show hook/config status and check identity or a message")
    check.add_argument("--message", metavar="FILE", help="also check this commit message file")
    check.add_argument("--command", help="also check a shell command that runs git commit")
    check.add_argument("--tool-json", action="store_true",
                       help="read a PreToolUse JSON payload on stdin; exit 2 to block")
    scan = gsub.add_parser("scan", help="check existing commits (default: @{upstream}..HEAD or HEAD)")
    scan.add_argument("revs", nargs="*", help="revision range(s), e.g. origin/main..HEAD")
    gsub.add_parser("uninstall", help="remove the hooks and restore any backed-up originals")
    hook = gsub.add_parser("hook", help=argparse.SUPPRESS)
    hook.add_argument("name", choices=["commit-msg", "pre-push"])
    hook.add_argument("args", nargs="*")

    kit = sub.add_parser("install", help="copy skills and templates into a project (preview by default)")
    kit.add_argument("--target", default=".", help="project directory (default: current directory)")
    kit.add_argument("--skills-dir", default=".claude/skills",
                     help="skills destination relative to target (default: .claude/skills)")
    kit.add_argument("--docs-dir", default="agent", help="templates destination relative to target")
    kit.add_argument("--no-guard", action="store_true", help="skip installing commit-guard hooks")
    kit.add_argument("--apply", action="store_true", help="actually write files (default is preview)")
    return parser


def _utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_streams()
    args = _parser().parse_args(argv)
    from agentkit.guard import config, git, hooks, runner

    try:
        if args.command == "install":
            from agentkit import installer

            return installer.run(args.target, args.skills_dir, args.docs_dir, not args.no_guard, args.apply)
        if args.action == "install":
            return hooks.install(force=args.force, write_config=not args.no_config)
        if args.action == "uninstall":
            return hooks.uninstall()
        if args.action == "check":
            return runner.check(args.message, args.command, args.tool_json)
        if args.action == "scan":
            return runner.scan(args.revs)
        if args.name == "commit-msg":
            if not args.args:
                print("commit-msg hook needs the message file path", file=sys.stderr)
                return 1
            return runner.hook_commit_msg(args.args[0])
        remote = args.args[0] if args.args else "origin"
        return runner.hook_pre_push(remote, sys.stdin.read())
    except (git.GitError, config.ConfigError) as exc:
        print(f"commit-guard: {exc}", file=sys.stderr)
        return 2
