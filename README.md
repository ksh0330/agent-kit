# agent-kit

[English summary](#english-summary)

코딩 에이전트와 함께 작업할 때 쓰는 작은 키트입니다. 외부 패키지 없이 Python 표준 라이브러리(3.10+)만 사용하고, Linux·macOS·Windows(Git for Windows)에서 동작합니다.

- **commit-guard**: 원치 않는 작성자와 자동 서명 문구가 Git 기록에 들어가지 않게 막는 훅
- **워크플로 스킬 6개**: `plan`, `build`, `review`, `verify`, `handoff`, `wrapup`
- **공유 문서 3개**: `BOARD.md`, `PLAN.md`, `LEARNING.md`. 사람과 에이전트가 같이 읽고 갱신합니다.

## 왜 필요한가

코딩 에이전트나 편집기 연동 도구는 설정에 따라 커밋에 흔적을 남깁니다. 도구 계정의 `Co-authored-by:` 트레일러, "generated with" 꼬리말, 세션 표시나 URL이 붙기도 하고, 작성자 정보가 아예 다르게 들어가기도 합니다. 한번 push하면 기록을 고치기가 번거롭습니다.

commit-guard는 커밋이 만들어지기 전에 한 번, push로 밖에 나가기 전에 한 번 더 검사합니다.

| 검사 | `commit-msg` | `pre-push` / `scan` |
|------|:---:|:---:|
| 메시지 각 줄을 `denied_trailer_patterns`(정규식)와 대조 | O | O |
| `Co-authored-by`, `Signed-off-by` 등에 적힌 사람을 `denied_names` / `denied_emails`와 대조 | O | O |
| 작성자·커미터를 `allowed_authors`와 금지 목록에 대조 | O | O |

## 빠른 시작

```sh
git clone https://github.com/ksh0330/agent-kit ~/agent-kit
cd /path/to/your/project
PYTHONPATH=~/agent-kit python3 -m agentkit guard install
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "C:\tools\agent-kit"
python -m agentkit guard install
```

`install`은 `.git/hooks`에 `commit-msg`와 `pre-push`를 설치합니다.

- 기존 훅이 있으면 덮어쓰지 않고 `<이름>.agentkit-backup`으로 옮긴 뒤 **먼저 실행**합니다(체이닝). 기존 훅이 실패하면 커밋도 막힙니다.
- `core.hooksPath`가 설정돼 있으면 Git이 `.git/hooks`를 무시하므로 설치를 거부합니다. `--force`로 강제할 수 있습니다.
- `.commit-guard.json`이 없으면 현재 `user.name` / `user.email`만 허용하는 설정 파일을 만듭니다.

### 명령어

```text
python -m agentkit guard install     # 훅 설치 (기존 훅은 백업 후 체이닝)
python -m agentkit guard check       # 설정, 훅 상태, 현재 사용자 확인
python -m agentkit guard check --message FILE      # 커밋 메시지 초안도 검사
python -m agentkit guard check --command "git commit -m ..."   # 명령어 한 줄 검사
python -m agentkit guard scan [범위 ...]           # 기본값: @{upstream}..HEAD, 없으면 HEAD
python -m agentkit guard uninstall   # 훅 제거, 백업 복원
```

### 설정: `.commit-guard.json`

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

- `allowed_authors`: 이메일은 필수, 이름은 선택입니다. 빈 목록이면 허용 목록 검사를 하지 않고 금지 목록만 적용합니다.
- `denied_names`: 대소문자 무시, 단어 단위로 일치시킵니다.
- `denied_emails`: 대소문자 무시, 셸 와일드카드(`*`)를 씁니다.
- `denied_trailer_patterns`: 대소문자 무시 정규식이며, 메시지의 모든 줄에 적용합니다.
- 설정한 키는 기본값을 **대체**하고, 생략한 키는 기본값을 유지합니다. 기본값은 [`agentkit/guard/config.py`](agentkit/guard/config.py)에 있습니다. 코딩 도우미 도구 이름이 들어간 co-author 트레일러, "generated with" 꼬리말, 세션 표시와 세션 URL을 막습니다.
- 설정 파일이 깨져 있으면 고칠 때까지 커밋을 막습니다.

예시는 [`.commit-guard.example.json`](.commit-guard.example.json)을 참고하세요.

### 출력 예시

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

`pre-push`는 원격에 아직 없는 커밋만 검사합니다. 기존 브랜치는 `원격..로컬` 범위를, 새 브랜치는 `refs/remotes/<원격>/*` 어디에도 없는 커밋을 봅니다.

## 스킬과 공유 문서 설치

```sh
./install.sh --target /path/to/project            # 미리보기: 무엇을 쓸지 보여주기만 함
./install.sh --target /path/to/project --apply    # 파일 복사 + 훅 설치
```

```powershell
.\install.ps1 --target C:\path\to\project
.\install.ps1 --target C:\path\to\project --apply
```

옵션: `--skills-dir`(기본 `.claude/skills`, 다른 도구는 `.agents/skills` 등), `--docs-dir`(기본 `agent`), `--no-guard`. 이미 있는 파일은 덮어쓰지 않습니다.

| 스킬 | 용도 |
|------|------|
| `plan` | 요청을 확인 가능한 수용 기준과 작은 단위 작업으로 정리 (`PLAN.md`) |
| `build` | 단위 작업 하나를 구현하고 검증한 뒤, 검증된 파일만 커밋 |
| `review` | 읽기 전용 리뷰. 근거 있는 문제만 심각도순으로 보고 |
| `verify` | 모든 수용 기준을 지금 실행한 결과와 대조 |
| `handoff` | 다음 사람이나 세션이 이어받을 수 있게 실제 상태를 기록 |
| `wrapup` | 마무리: 검증, 문서와 동작 대조, 교훈 기록, 솔직한 요약 |

작업은 단위마다 계획 → 구현 → 검증 → 리뷰를 반복합니다. `BOARD.md`에는 현재 상태를, `PLAN.md`에는 기준과 단위 작업을, `LEARNING.md`에는 다음 작업 방식을 바꿀 교훈을 적습니다. Git 관련 규칙은 기억에 맡기지 않고 commit-guard가 강제합니다.

편집기 설정 예시(선택): [docs/CLAUDE_CODE.md](docs/CLAUDE_CODE.md)

## 한계

- **`git commit --no-verify`, `git push --no-verify`는 훅을 건너뜁니다.** 로컬 훅은 실수를 막는 안전망이지 보안 장치가 아닙니다. 이중 확인이 필요하면 CI에서 `guard scan`을 돌리세요.
- **훅은 클론으로 따라가지 않습니다.** `.git/hooks`는 버전 관리 대상이 아니므로 클론할 때마다 `guard install`을 해야 합니다. 규칙을 공유하려면 `.commit-guard.json`을 커밋하세요.
- **서버 측 차단이 아닙니다.** 다른 컴퓨터에서 하는 push는 막지 못합니다. 확실히 막으려면 호스팅 서비스의 pre-receive 훅이나 필수 CI 검사를 쓰세요.
- `commit-msg`는 Git 기본 메시지 정리 방식(주석 줄, 가위 표시)을 흉내 냅니다. `commit.cleanup`이나 주석 문자를 바꿨다면 주석 줄 처리가 다를 수 있습니다.
- rebase, cherry-pick, amend에도 `commit-msg`가 실행됩니다. `--no-verify`로 만든 merge는 검사하지 않습니다.
- 훅에는 설치 당시 Python 경로와 키트 위치가 절대 경로로 기록됩니다. 둘 중 하나를 옮기면 `guard install`을 다시 실행하세요.

## 개발

```sh
python -m unittest discover -s tests -t tests -v
```

테스트는 Git 설정을 격리한 임시 저장소를 만들고, 설치한 훅을 거쳐 실제 `git commit` / `git push`를 실행합니다.

## 라이선스

MIT. [LICENSE](LICENSE)를 참고하세요.

## English summary

agent-kit is a small, dependency-free kit (Python 3.10+ standard library) for working with coding agents:

- **commit-guard**: `commit-msg` and `pre-push` hooks that reject denied attribution text (co-author trailers for tool accounts, "generated with" footers, session markers) and authors or committers outside `allowed_authors`. `pre-push` scans only the commits being pushed.
- **Six skills** (`plan`, `build`, `review`, `verify`, `handoff`, `wrapup`) and **three shared docs** (`BOARD.md`, `PLAN.md`, `LEARNING.md`).

```sh
PYTHONPATH=/path/to/agent-kit python3 -m agentkit guard install   # hooks; existing ones are backed up and chained
./install.sh --target /path/to/project [--apply]                   # skills + docs; preview unless --apply
```

Limits: `--no-verify` bypasses the hooks, hooks are not cloned with the repo, and this is not server-side enforcement. License: MIT.

## Acknowledgements

The plan-build-verify-review loop, hook-enforced rules and a learning log are ideas inspired by [ECC](https://github.com/affaan-m/ECC).
