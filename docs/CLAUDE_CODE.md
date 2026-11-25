# Optional: Claude Code settings

commit-guard works with any Git client. If you use Claude Code, two optional settings
stop attribution text from being added in the first place and check `git commit`
commands before they run. Both go in `.claude/settings.json` (shared with the project)
or `.claude/settings.local.json` (just you). Check the current settings reference for
your version; key names have changed between releases.

## 1. Empty attribution

Empty strings disable the default commit and pull request footers:

```json
{
  "attribution": {
    "commit": "",
    "pr": ""
  }
}
```

Older versions used a boolean instead:

```json
{
  "includeCoAuthoredBy": false
}
```

## 2. Pre-check `git commit` in the Bash tool

A `PreToolUse` hook receives the pending tool call as JSON on stdin. `guard check --tool-json`
reads that payload, ignores commands that are not `git commit`, and exits with code 2
(which blocks the call and shows the reason) when the message, `--author`, `-c user.*`
identity or `--no-verify` would break the rules in `.commit-guard.json`.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "PYTHONPATH=/path/to/agent-kit python3 -m agentkit guard check --tool-json"
          }
        ]
      }
    ]
  }
}
```

On Windows, replace the command with a PowerShell form, for example
`powershell -NoProfile -Command "$env:PYTHONPATH='C:\path\to\agent-kit'; python -m agentkit guard check --tool-json"`.

Try it by hand:

```sh
echo '{"tool_input": {"command": "git commit -m \"fix: x\" --no-verify"}}' \
  | PYTHONPATH=/path/to/agent-kit python3 -m agentkit guard check --tool-json
echo "exit=$?"   # 2 -> blocked
```

This pre-check is a convenience. The Git hooks installed by `guard install` remain the
actual enforcement point, and they also cover commits made outside the tool.
