"""Thin wrappers around the git command line."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

ZERO_SHA = "0" * 40


class GitError(Exception):
    pass


def run(args: list[str], cwd: Path | str | None = None, check: bool = True, stdin: str | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or f"git {' '.join(args)} failed ({proc.returncode})")
    return proc.stdout if proc.returncode == 0 else ""


def toplevel(cwd: Path | str | None = None) -> Path:
    return Path(run(["rev-parse", "--show-toplevel"], cwd).strip())


def hooks_dir(cwd: Path | str | None = None) -> Path:
    """The repository's own hooks directory, ignoring core.hooksPath."""
    common = Path(run(["rev-parse", "--git-common-dir"], cwd).strip())
    if not common.is_absolute():
        common = Path(cwd or ".").resolve() / common
    return common / "hooks"


def config_get(key: str, cwd: Path | str | None = None) -> str:
    return run(["config", "--get", key], cwd, check=False).strip()


def var_ident(which: str, cwd: Path | str | None = None) -> str:
    """Return ``git var GIT_AUTHOR_IDENT`` / ``GIT_COMMITTER_IDENT`` (empty if unset)."""
    return run(["var", which], cwd, check=False).strip()


@dataclass(frozen=True)
class Commit:
    sha: str
    author: tuple[str, str]
    committer: tuple[str, str]
    message: str

    @property
    def subject(self) -> str:
        return self.message.split("\n", 1)[0]


def commits(revs: list[str], cwd: Path | str | None = None) -> list[Commit]:
    fmt = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e"
    out = run(["log", f"--format={fmt}", *revs, "--"], cwd)
    result = []
    for record in out.split("\x1e"):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, an, ae, cn, ce, body = record.split("\x1f", 5)
        result.append(Commit(sha, (an, ae), (cn, ce), body.strip("\n")))
    return result


def rev_exists(rev: str, cwd: Path | str | None = None) -> bool:
    return bool(run(["rev-parse", "--verify", "--quiet", rev + "^{commit}"], cwd, check=False).strip())
