"""Shared fixtures: throwaway Git repositories with an isolated Git configuration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOOD = ("Alice Example", "alice@example.com")
OTHER = ("Bob Example", "bob@example.com")


class GitCase(unittest.TestCase):
    """Each test gets a fresh repo with alice as the configured identity."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="agentkit-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        gitconfig = self.tmp / "gitconfig"
        gitconfig.write_text("", encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "PYTHONPATH"))}
        self.env.update({"GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1",
                         "HOME": str(self.tmp), "PYTHONPATH": str(ROOT)})
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", GOOD[0])
        self.git("config", "user.email", GOOD[1])
        self.git("config", "core.autocrlf", "false")

    def git(self, *args: str, cwd: Path | None = None, check: bool = True, stdin: str | None = None,
            env: dict | None = None) -> subprocess.CompletedProcess:
        proc = subprocess.run(["git", *args], cwd=cwd or self.repo, env={**self.env, **(env or {})},
                              input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if check and proc.returncode != 0:
            self.fail(f"git {' '.join(args)} failed: {proc.stdout}{proc.stderr}")
        return proc

    def kit(self, *args: str, cwd: Path | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-m", "agentkit", *args], cwd=cwd or self.repo, env=self.env,
                              input=stdin, capture_output=True, text=True, encoding="utf-8", errors="replace")

    def write_config(self, **overrides) -> None:
        data = {"allowed_authors": [{"name": GOOD[0], "email": GOOD[1]}]}
        data.update(overrides)
        (self.repo / ".commit-guard.json").write_text(json.dumps(data), encoding="utf-8")

    def commit(self, message: str, *extra: str, check: bool = False, env: dict | None = None,
               filename: str | None = None) -> subprocess.CompletedProcess:
        name = filename or f"f{len(list(self.repo.glob('f*.txt')))}.txt"
        (self.repo / name).write_text(message[:20] + "\n", encoding="utf-8")
        self.git("add", name)
        msg = self.tmp / "msg.txt"
        msg.write_text(message, encoding="utf-8")
        return self.git("commit", "-q", "-F", str(msg), *extra, check=check, env=env)

    def install_guard(self) -> subprocess.CompletedProcess:
        proc = self.kit("guard", "install")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def head_count(self) -> int:
        proc = self.git("rev-list", "--count", "HEAD", check=False)
        return int(proc.stdout.strip()) if proc.returncode == 0 else 0

    def write_hook(self, name: str, body: str) -> Path:
        path = self.repo / ".git" / "hooks" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8", newline="\n")
        path.chmod(0o755)
        return path
