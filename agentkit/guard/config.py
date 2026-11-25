"""Loading and validating .commit-guard.json."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

CONFIG_NAME = ".commit-guard.json"

# Tool names that commonly show up in automatic attribution footers.
_TOOLS = r"(claude|anthropic|codex|openai|copilot|chatgpt)"

DEFAULT_CONFIG: dict = {
    # Empty list means "no allow-list": every identity not explicitly denied passes.
    "allowed_authors": [],
    # Case-insensitive whole-word match against identity names.
    "denied_names": ["claude", "anthropic", "codex", "openai", "copilot", "chatgpt"],
    # Case-insensitive shell-style globs against identity emails.
    "denied_emails": [
        "*@anthropic.com",
        "*@openai.com",
        "*claude*@*",
        "*codex*@*",
        "*copilot*@*",
    ],
    # Case-insensitive regular expressions, applied to every message line.
    "denied_trailer_patterns": [
        r"^\s*co-authored-by:.*" + _TOOLS,
        r"generated with",
        r"claude-session",
        r"https?://(www\.)?claude\.ai/\S*",
        r"^\s*(assisted|generated|made)-by:.*" + _TOOLS,
    ],
}

_LIST_KEYS = ("denied_names", "denied_emails", "denied_trailer_patterns")


class ConfigError(Exception):
    """Raised when the configuration file is unreadable or malformed."""


def default_config() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)


def validate(data: object) -> dict:
    """Return a normalised config built from defaults plus ``data``.

    Keys present in ``data`` replace the defaults entirely; missing keys keep them.
    """
    if not isinstance(data, dict):
        raise ConfigError("top level must be a JSON object")
    unknown = sorted(set(data) - set(DEFAULT_CONFIG) - {"$comment"})
    if unknown:
        raise ConfigError("unknown key(s): " + ", ".join(unknown))
    cfg = default_config()
    authors = data.get("allowed_authors", cfg["allowed_authors"])
    if not isinstance(authors, list):
        raise ConfigError("allowed_authors must be a list")
    normalised = []
    for index, entry in enumerate(authors):
        if not isinstance(entry, dict) or not isinstance(entry.get("email"), str) or not entry["email"].strip():
            raise ConfigError(f"allowed_authors[{index}] needs an 'email' string")
        name = entry.get("name")
        if name is not None and not isinstance(name, str):
            raise ConfigError(f"allowed_authors[{index}].name must be a string")
        normalised.append({"name": (name or "").strip(), "email": entry["email"].strip()})
    cfg["allowed_authors"] = normalised
    for key in _LIST_KEYS:
        value = data.get(key, cfg[key])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ConfigError(f"{key} must be a list of strings")
        cfg[key] = list(value)
    for pattern in cfg["denied_trailer_patterns"]:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ConfigError(f"bad regular expression {pattern!r}: {exc}") from None
    return cfg


def load(root: Path) -> tuple[dict, Path | None]:
    """Load the config from ``root``. Returns (config, path or None when defaults are used)."""
    path = Path(root) / CONFIG_NAME
    if not path.exists():
        return default_config(), None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"{path.name}: {exc}") from None
    try:
        return validate(data), path
    except ConfigError as exc:
        raise ConfigError(f"{path.name}: {exc}") from None


def write_default(root: Path, allowed: list[dict]) -> Path:
    cfg = default_config()
    cfg["allowed_authors"] = allowed
    path = Path(root) / CONFIG_NAME
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path
