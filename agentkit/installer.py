"""Copy skills and shared templates into a project. Preview unless apply=True. Never overwrites."""

from __future__ import annotations

import shutil
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]


def plan(target: Path, skills_dir: str, docs_dir: str) -> list[tuple[Path, Path, str]]:
    actions = []
    for skill in sorted((KIT_ROOT / "skills").glob("*/SKILL.md")):
        dest = target / skills_dir / skill.parent.name / "SKILL.md"
        actions.append((skill, dest, "skip (exists)" if dest.exists() else "copy"))
    for template in sorted((KIT_ROOT / "templates").glob("*.md")):
        dest = target / docs_dir / template.name
        actions.append((template, dest, "skip (exists)" if dest.exists() else "copy"))
    return actions


def run(target: str, skills_dir: str, docs_dir: str, guard: bool, apply: bool, out=print) -> int:
    root = Path(target).resolve()
    if not root.is_dir():
        out(f"error: target {root} is not a directory")
        return 2
    mode = "APPLY" if apply else "PREVIEW (nothing is written; rerun with --apply)"
    out(f"agent-kit install -> {root}  [{mode}]")
    for source, dest, action in plan(root, skills_dir, docs_dir):
        out(f"  {action:14} {dest.relative_to(root).as_posix()}")
        if apply and action == "copy":
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
    if not guard:
        return 0
    if not (root / ".git").exists():
        out("  skip           commit-guard hooks (target is not a Git repository root)")
        return 0
    if not apply:
        out("  install        commit-guard hooks into .git/hooks (existing hooks are backed up and chained)")
        return 0
    from agentkit.guard import hooks

    return hooks.install(root, out=lambda line: out("  " + line))
