"""Pure checks for commit messages and identities. No Git calls here."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass

SCISSORS = "------------------------ >8 ------------------------"
TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*)\s*:\s*(.*)$")
IDENT_RE = re.compile(r"^(.*?)\s*<([^<>]*)>")
# Trailers whose value names a person; their identities are checked too.
PERSON_TRAILERS = {
    "co-authored-by",
    "signed-off-by",
    "reviewed-by",
    "acked-by",
    "tested-by",
    "helped-by",
    "suggested-by",
    "reported-by",
}


@dataclass(frozen=True)
class Violation:
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule}: {self.detail}"


def clean_message(text: str, strip_comments: bool = True) -> str:
    """Approximate Git's default cleanup: drop comment lines and the scissors section."""
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if strip_comments and line.startswith("#"):
            if SCISSORS in line:
                break
            continue
        lines.append(line)
    return "\n".join(lines).strip("\n")


def parse_ident(value: str) -> tuple[str, str]:
    """Split ``Name <email> [rest]`` into (name, email). Missing parts become ''."""
    match = IDENT_RE.match(value.strip())
    if not match:
        return value.strip(), ""
    return match.group(1).strip(), match.group(2).strip()


def denied_reasons(name: str, email: str, cfg: dict) -> list[str]:
    reasons = []
    for word in cfg["denied_names"]:
        if word and re.search(r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])", name.lower()):
            reasons.append(f"name matches denied name '{word}'")
    for pattern in cfg["denied_emails"]:
        if email and fnmatch.fnmatchcase(email.lower(), pattern.lower()):
            reasons.append(f"email matches denied pattern '{pattern}'")
    return reasons


def is_allowed(name: str, email: str, cfg: dict) -> bool:
    allowed = cfg["allowed_authors"]
    if not allowed:
        return True
    for entry in allowed:
        if entry["email"].lower() != email.lower():
            continue
        if not entry["name"] or entry["name"] == name.strip():
            return True
    return False


def check_identity(role: str, name: str, email: str, cfg: dict) -> list[Violation]:
    """Check an author/committer identity against deny lists and the allow-list."""
    who = f"{role} '{name} <{email}>'"
    found = [Violation("denied-user", f"{who}: {reason}") for reason in denied_reasons(name, email, cfg)]
    if not is_allowed(name, email, cfg):
        found.append(Violation("author-not-allowed", f"{who} is not in allowed_authors"))
    return found


def check_message(message: str, cfg: dict) -> list[Violation]:
    """Check message body and trailers for denied patterns and denied people."""
    patterns = [re.compile(p, re.IGNORECASE) for p in cfg["denied_trailer_patterns"]]
    found: list[Violation] = []
    for number, line in enumerate(message.split("\n"), start=1):
        text = line.strip()
        if not text:
            continue
        for pattern in patterns:
            if pattern.search(line):
                found.append(Violation("denied-pattern", f"line {number} matches /{pattern.pattern}/: {text[:120]}"))
        trailer = TRAILER_RE.match(text)
        if trailer and trailer.group(1).lower() in PERSON_TRAILERS:
            name, email = parse_ident(trailer.group(2))
            for reason in denied_reasons(name, email, cfg):
                found.append(Violation("denied-user", f"line {number} {trailer.group(1)} '{trailer.group(2)}': {reason}"))
    return found


def check_commit(message: str, author: tuple[str, str], committer: tuple[str, str], cfg: dict) -> list[Violation]:
    found = check_identity("author", author[0], author[1], cfg)
    if committer != author:
        found += check_identity("committer", committer[0], committer[1], cfg)
    found += check_message(message, cfg)
    return found
