"""Installing and removing commit-guard hooks in .git/hooks, with backup and chaining."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

from agentkit.guard import config, git

MARKER = "# agentkit-commit-guard"
HOOK_NAMES = ("commit-msg", "pre-push")
BACKUP_SUFFIX = ".agentkit-backup"
KIT_HOME = Path(__file__).resolve().parents[2]


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def render(name: str, python: str | None = None, home: Path | None = None) -> str:
    python = _posix(python or sys.executable)
    home = _posix(home or KIT_HOME)
    head = (
        "#!/bin/sh\n"
        f"{MARKER}: managed hook. Remove with: python -m agentkit guard uninstall\n"
        f"AGENTKIT_PY={_sh_quote(python)}\n"
        f"AGENTKIT_HOME={_sh_quote(home)}\n"
        'backup="$(dirname -- "$0")/' + name + BACKUP_SUFFIX + '"\n'
    )
    run = '"$AGENTKIT_PY" -m agentkit guard hook ' + name + ' "$@"'
    tail = 'PYTHONPATH="$AGENTKIT_HOME"\nexport PYTHONPATH\n'
    if name == "pre-push":
        # stdin carries the ref list; capture it once and feed both hooks.
        return head + (
            "input=$(cat)\n"
            'if [ -f "$backup" ]; then\n'
            '  printf \'%s\\n\' "$input" | "$backup" "$@" || exit $?\n'
            "fi\n" + tail +
            'printf \'%s\\n\' "$input" | ' + run + "\n"
        )
    return head + (
        'if [ -f "$backup" ]; then\n'
        '  "$backup" "$@" || exit $?\n'
        "fi\n" + tail +
        "exec " + run + "\n"
    )


def is_ours(path: Path) -> bool:
    try:
        return MARKER in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install(cwd: Path | str | None = None, force: bool = False, write_config: bool = True, out=print) -> int:
    root = git.toplevel(cwd)
    hooks_path = git.config_get("core.hooksPath", root)
    if hooks_path:
        out(f"warning: core.hooksPath is set to '{hooks_path}'; Git will not run hooks from .git/hooks.")
        if not force:
            out("refusing to install. Unset it (git config --unset core.hooksPath) or pass --force.")
            return 2
    directory = git.hooks_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    plan = []
    for name in HOOK_NAMES:
        target = directory / name
        backup = directory / (name + BACKUP_SUFFIX)
        if target.exists() and not is_ours(target):
            if backup.exists():
                out(f"error: {target} exists and {backup.name} is already taken; resolve manually.")
                return 2
            plan.append((name, target, backup))
        else:
            plan.append((name, target, None))
    for name, target, backup in plan:
        if backup is not None:
            os.replace(target, backup)
            out(f"backed up existing {name} -> {backup.name} (it will run first)")
        existed = target.exists()
        target.write_text(render(name), encoding="utf-8", newline="\n")
        _make_executable(target)
        out(f"{'updated' if existed else 'installed'} {_posix(target)}")
    if write_config and not (root / config.CONFIG_NAME).exists():
        name = git.config_get("user.name", root)
        email = git.config_get("user.email", root)
        allowed = [{"name": name, "email": email}] if name and email else []
        path = config.write_default(root, allowed)
        who = f"{name} <{email}>" if allowed else "nobody (allow-list disabled)"
        out(f"created {path.name}; allowed_authors: {who}. Review and commit it.")
    return 0


def uninstall(cwd: Path | str | None = None, out=print) -> int:
    directory = git.hooks_dir(git.toplevel(cwd))
    for name in HOOK_NAMES:
        target = directory / name
        backup = directory / (name + BACKUP_SUFFIX)
        if target.exists() and not is_ours(target):
            out(f"left {name} alone (not managed by commit-guard)")
            continue
        if target.exists():
            target.unlink()
            out(f"removed {name}")
        if backup.exists():
            os.replace(backup, target)
            out(f"restored original {name} from {backup.name}")
    return 0


def status(cwd: Path | str | None = None) -> dict[str, str]:
    directory = git.hooks_dir(git.toplevel(cwd))
    result = {}
    for name in HOOK_NAMES:
        target = directory / name
        if not target.exists():
            state = "not installed"
        elif is_ours(target):
            state = "installed"
            if (directory / (name + BACKUP_SUFFIX)).exists():
                state += " (chained to backup)"
        else:
            state = "foreign hook present (commit-guard not installed)"
        result[name] = state
    return result
