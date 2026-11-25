"""Entry points used by the hooks and the CLI: commit-msg, pre-push, scan, check."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

from agentkit.guard import config, git, hooks, rules

PREFIX = "commit-guard"


def _err(text: str = "") -> None:
    print(text, file=sys.stderr)


def _load(root: Path) -> dict | None:
    try:
        return config.load(root)[0]
    except config.ConfigError as exc:
        _err(f"{PREFIX}: config error: {exc}")
        _err(f"{PREFIX}: refusing to continue until the config is fixed.")
        return None


def report(problems: list[tuple[git.Commit | None, list[rules.Violation]]], stream=None) -> None:
    stream = stream or sys.stderr
    total = sum(len(v) for _, v in problems)
    print(f"{PREFIX}: {total} problem(s) in {len(problems)} commit(s)", file=stream)
    for commit, violations in problems:
        if commit is not None:
            print(f"  {commit.sha[:12]}  {commit.subject[:72]}", file=stream)
        for violation in violations:
            print(f"    - {violation}", file=stream)


# --- commit-msg -------------------------------------------------------------

def hook_commit_msg(message_file: str) -> int:
    root = git.toplevel()
    cfg = _load(root)
    if cfg is None:
        return 1
    raw = Path(message_file).read_text(encoding="utf-8", errors="replace")
    message = rules.clean_message(raw)
    author = rules.parse_ident(git.var_ident("GIT_AUTHOR_IDENT", root))
    committer = rules.parse_ident(git.var_ident("GIT_COMMITTER_IDENT", root))
    violations = rules.check_commit(message, author, committer, cfg)
    if not violations:
        return 0
    _err(f"{PREFIX}: commit rejected")
    report([(None, violations)])
    _err(f"{PREFIX}: edit the message or identity and commit again. Message kept in {message_file}.")
    return 1


# --- pre-push / scan --------------------------------------------------------

def push_ranges(stdin_text: str, remote: str, root: Path) -> list[list[str]]:
    """Translate pre-push stdin lines into rev arguments for ``git log``."""
    ranges = []
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        if local_sha == git.ZERO_SHA:
            continue  # branch deletion: nothing new is sent
        if remote_sha != git.ZERO_SHA and git.rev_exists(remote_sha, root):
            ranges.append([f"{remote_sha}..{local_sha}"])
        else:
            # New branch or unknown remote tip: everything not already on that remote.
            ranges.append([local_sha, "--not", f"--remotes={remote}"])
    return ranges


def scan_revs(revs: list[str], root: Path, cfg: dict) -> list[tuple[git.Commit, list[rules.Violation]]]:
    found = []
    for commit in git.commits(revs, root):
        violations = rules.check_commit(commit.message, commit.author, commit.committer, cfg)
        if violations:
            found.append((commit, violations))
    return found


def hook_pre_push(remote: str, stdin_text: str) -> int:
    root = git.toplevel()
    cfg = _load(root)
    if cfg is None:
        return 1
    problems = []
    seen = set()
    for revs in push_ranges(stdin_text, remote, root):
        for commit, violations in scan_revs(revs, root, cfg):
            if commit.sha not in seen:
                seen.add(commit.sha)
                problems.append((commit, violations))
    if not problems:
        return 0
    _err(f"{PREFIX}: push rejected")
    report(problems)
    _err(f"{PREFIX}: rewrite those commits (e.g. git rebase -i / git commit --amend) and push again.")
    return 1


def default_scan_revs(root: Path) -> list[str]:
    upstream = git.run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], root, check=False).strip()
    return ["@{upstream}..HEAD"] if upstream else ["HEAD"]


def scan(revs: list[str], cwd: Path | str | None = None) -> int:
    root = git.toplevel(cwd)
    cfg = _load(root)
    if cfg is None:
        return 1
    revs = revs or default_scan_revs(root)
    try:
        problems = scan_revs(revs, root, cfg)
        count = len(git.commits(revs, root))
    except git.GitError as exc:
        _err(f"{PREFIX}: {exc}")
        return 2
    if problems:
        report(problems, sys.stdout)
        return 1
    print(f"{PREFIX}: {count} commit(s) in {' '.join(revs)} are clean")
    return 0


# --- check ------------------------------------------------------------------

_SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}


def _git_commit_calls(command: str) -> list[tuple[dict, list[str]]]:
    """Find ``git [-c k=v] [-C dir] commit ...`` invocations in a shell command line."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments, current = [], []
    for token in tokens:
        if token in _SEPARATORS or set(token) <= set("&|;"):
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    calls = []
    for segment in segments:
        if not segment or Path(segment[0]).name.lower() not in ("git", "git.exe"):
            continue
        settings, index = {}, 1
        while index < len(segment) and segment[index].startswith("-"):
            option = segment[index]
            if option in ("-c", "-C") and index + 1 < len(segment):
                if option == "-c" and "=" in segment[index + 1]:
                    key, value = segment[index + 1].split("=", 1)
                    settings[key.lower()] = value
                elif option == "-C":
                    settings["-C"] = segment[index + 1]
                index += 2
            else:
                index += 1
        if index < len(segment) and segment[index] == "commit":
            calls.append((settings, segment[index + 1:]))
    return calls


def precheck_command(command: str, cfg: dict, cwd: Path | str | None = None) -> list[rules.Violation]:
    """Check a shell command that may run ``git commit`` before it executes."""
    found: list[rules.Violation] = []
    base = Path(cwd or ".")
    for settings, args in _git_commit_calls(command):
        messages, index = [], 0
        while index < len(args):
            arg = args[index]
            nxt = args[index + 1] if index + 1 < len(args) else ""
            if arg in ("-m", "--message"):
                messages.append(nxt)
                index += 1
            elif arg.startswith("--message="):
                messages.append(arg.split("=", 1)[1])
            elif arg.startswith("-m") and len(arg) > 2 and not arg.startswith("--"):
                messages.append(arg[2:])
            elif arg in ("-F", "--file") or arg.startswith("--file="):
                name = arg.split("=", 1)[1] if "=" in arg else nxt
                index += 0 if "=" in arg else 1
                path = base / settings.get("-C", ".") / name
                if path.is_file():
                    messages.append(path.read_text(encoding="utf-8", errors="replace"))
            elif arg in ("--no-verify", "-n"):
                found.append(rules.Violation("no-verify", "git commit --no-verify skips commit-guard hooks"))
            elif arg.startswith("--author="):
                name, email = rules.parse_ident(arg.split("=", 1)[1])
                found += rules.check_identity("author", name, email, cfg)
            index += 1
        name = settings.get("user.name") or git.config_get("user.name", base)
        email = settings.get("user.email") or git.config_get("user.email", base)
        found += rules.check_identity("committer", name, email, cfg)
        found += rules.check_message(rules.clean_message("\n\n".join(messages)), cfg)
    return found


def check(message_file: str | None = None, command: str | None = None, tool_json: bool = False,
          cwd: Path | str | None = None) -> int:
    if tool_json:
        return check_tool_json(sys.stdin.read())
    root = git.toplevel(cwd)
    try:
        cfg, path = config.load(root)
    except config.ConfigError as exc:
        print(f"{PREFIX}: config error: {exc}")
        return 1
    print(f"config: {path.name if path else 'built-in defaults (no ' + config.CONFIG_NAME + ')'}")
    print(f"allowed_authors: {len(cfg['allowed_authors']) or 'any (allow-list disabled)'}")
    hooks_path = git.config_get("core.hooksPath", root)
    if hooks_path:
        print(f"warning: core.hooksPath={hooks_path}; hooks in .git/hooks are ignored")
    for name, state in hooks.status(root).items():
        print(f"hook {name}: {state}")
    problems: list[rules.Violation] = []
    name, email = git.config_get("user.name", root), git.config_get("user.email", root)
    problems += rules.check_identity("current identity", name, email, cfg)
    if message_file:
        text = Path(message_file).read_text(encoding="utf-8", errors="replace")
        problems += rules.check_message(rules.clean_message(text), cfg)
    if command:
        problems += precheck_command(command, cfg, root)
    if problems:
        report([(None, problems)], sys.stdout)
        return 1
    print(f"{PREFIX}: ok")
    return 0


def check_tool_json(payload: str) -> int:
    """PreToolUse-style hook: JSON on stdin with tool_input.command. Exit 2 blocks the call."""
    try:
        data = json.loads(payload or "{}")
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    if "commit" not in command:
        return 0
    cwd = data.get("cwd") or "."
    try:
        cfg = config.load(git.toplevel(cwd))[0]
    except (config.ConfigError, git.GitError) as exc:
        _err(f"{PREFIX}: cannot check this commit: {exc}")
        return 2
    violations = precheck_command(command, cfg, cwd)
    if not violations:
        return 0
    _err(f"{PREFIX}: blocked git commit before it ran")
    report([(None, violations)])
    return 2
