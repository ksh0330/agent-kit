# agent-kit

A small, dependency-free kit for working with coding agents in any project:

- **commit-guard** - Git hooks that keep unwanted authors and automatic attribution text out of your history.
- **Six workflow skills** - `plan`, `build`, `review`, `verify`, `handoff`, `wrapup`.
- **Three shared documents** - `BOARD.md`, `PLAN.md`, `LEARNING.md`, read and updated by people and agents alike.

Pure Python standard library (3.10+). Works on Linux, macOS and Windows (Git for Windows).

## The problem

Coding agents and editor integrations like to sign their work. Depending on settings, a commit can
end up with a `Co-authored-by:` trailer for a tool account, a "generated with" footer, a session
marker or URL, or the wrong author identity entirely. Once pushed, rewriting that history is painful.

commit-guard checks every commit locally, before it exists, and again before it leaves the machine:

| Check | `commit-msg` | `pre-push` / `scan` |
|-------|:---:|:---:|
| Message lines against `denied_trailer_patterns` (regex) | yes | yes |
| People in `Co-authored-by`, `Signed-off-by`, ... against `denied_names` / `denied_emails` | yes | yes |
| Author and committer against `allowed_authors` and the deny lists | yes | yes |

## Quick start

```sh
git clone <this repository> ~/agent-kit
cd /path/to/your/project
PYTHONPATH=~/agent-kit python3 -m agentkit guard install
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "C:\tools\agent-kit"
python -m agentkit guard install
```

`install` writes `commit-msg` and `pre-push` into `.git/hooks`. If a hook already exists it is
renamed to `<name>.agentkit-backup` and **runs first** (chained); its failure still blocks.
If `core.hooksPath` is set, Git would ignore `.git/hooks`, so install refuses unless you pass `--force`.
If there is no `.commit-guard.json`, one is created that allows only your current `user.name` / `user.email`.

### Commands

```text
python -m agentkit guard install     # install hooks (backup + chain existing ones)
python -m agentkit guard check       # config, hook status, current identity
python -m agentkit guard check --message FILE      # also check a draft message
python -m agentkit guard check --command "git commit -m ..."   # check a command line
python -m agentkit guard scan [RANGE ...]          # default: @{upstream}..HEAD, else HEAD
python -m agentkit guard uninstall   # remove hooks, restore backups
```

### Configuration: `.commit-guard.json`

```json
{
  "allowed_authors": [
    {"name": "Alice Example", "email": "alice@example.com"},
    {"email": "build-bot@example.com"}
  ],
  "denied_names": ["mallory"],
  "denied_emails": ["*@blocked.example.com"],
  "denied_trailer_patterns": ["generated with", "^\\s*co-authored-by:.*\\bbot\\b"]
}
```

- `allowed_authors`: email required, name optional. Empty list = no allow-list (deny lists still apply).
- `denied_names`: case-insensitive, whole word.
- `denied_emails`: case-insensitive shell globs.
- `denied_trailer_patterns`: case-insensitive regular expressions, tested against every message line.
- Keys you set **replace** the defaults; keys you omit keep them. Defaults live in
  [`agentkit/guard/config.py`](agentkit/guard/config.py) and cover co-author trailers that name
  common assistant tools, "generated with" footers, session markers and session URLs.
- A broken config blocks commits (fail closed) until it is fixed.

See [`.commit-guard.example.json`](.commit-guard.example.json).

### Example output

```text
$ git commit -F msg.txt
commit-guard: commit rejected
commit-guard: 1 problem(s) in 1 commit(s)
    - denied-pattern: line 3 matches /generated with/: Generated with SomeTool
commit-guard: edit the message or identity and commit again. Message kept in .git/COMMIT_EDITMSG.

$ git commit -m "fix: y" --author="Bob Example <bob@example.com>"
commit-guard: commit rejected
commit-guard: 1 problem(s) in 1 commit(s)
    - author-not-allowed: author 'Bob Example <bob@example.com>' is not in allowed_authors

$ git push origin main
commit-guard: push rejected
commit-guard: 1 problem(s) in 1 commit(s)
  9e8b36084d24  fix: y
    - denied-pattern: line 3 matches /generated with/: Generated with SomeTool
commit-guard: rewrite those commits (e.g. git rebase -i / git commit --amend) and push again.
error: failed to push some refs to '../remote.git'

$ python -m agentkit guard check
config: .commit-guard.json
allowed_authors: 1
hook commit-msg: installed
hook pre-push: installed
commit-guard: ok
```

`pre-push` only scans commits that the remote does not have yet: `remote..local` for an existing
branch, and everything not on any `refs/remotes/<remote>/*` for a new one.

## Skills and shared documents

```sh
./install.sh --target /path/to/project            # preview: lists what would be written
./install.sh --target /path/to/project --apply    # copy files and install the hooks
```

```powershell
.\install.ps1 --target C:\path\to\project
.\install.ps1 --target C:\path\to\project --apply
```

Options: `--skills-dir` (default `.claude/skills`; use e.g. `.agents/skills` for other tools),
`--docs-dir` (default `agent`), `--no-guard`. Existing files are never overwritten.

| Skill | Use it to |
|-------|-----------|
| `plan` | turn a request into acceptance criteria and small slices (`PLAN.md`) |
| `build` | implement and verify one slice, commit only verified files |
| `review` | read-only, evidence-backed findings ordered by severity |
| `verify` | match every criterion against fresh command output |
| `handoff` | preserve the real state for the next person or session |
| `wrapup` | close out: verify, reconcile docs, record lessons, honest summary |

The loop is plan -> build -> verify -> review, repeated per slice. `BOARD.md` holds the current
state, `PLAN.md` the criteria and slices, and `LEARNING.md` the lessons that should change how the
next slice is done. commit-guard enforces the Git part of the rules instead of relying on memory.

Optional editor settings: [docs/CLAUDE_CODE.md](docs/CLAUDE_CODE.md).

## Limitations

- **`git commit --no-verify` and `git push --no-verify` skip the hooks.** Local hooks are a safety
  net against accidents, not a security boundary. Run `guard scan` in CI if you need a second check.
- **Hooks do not travel with clones.** `.git/hooks` is not versioned; every clone must run
  `guard install` (commit `.commit-guard.json` so the rules are shared).
- **Not server-side.** Nothing here stops a push made from another machine. For hard enforcement use
  a server-side pre-receive hook or a required CI check on your hosting platform.
- `commit-msg` approximates Git's default message cleanup (comment lines, scissors). Custom
  `commit.cleanup` modes or comment characters may let a commented line be checked or skipped differently.
- Rebases, cherry-picks and amends run `commit-msg` too; merges made with `--no-verify` do not.
- The hook records the absolute Python path and kit location used at install time. Re-run
  `guard install` after moving either.

## Development

```sh
python -m unittest discover -s tests -t tests -v
```

Tests create throwaway repositories with an isolated Git configuration and drive real
`git commit` / `git push` through the installed hooks.

## License

MIT - see [LICENSE](LICENSE).

## Acknowledgements

The plan-build-verify-review loop, hook-enforced rules and a learning log are ideas inspired by [ECC](https://github.com/affaan-m/ECC).
