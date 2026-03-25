# zshrc_best

모던 CLI 도구들로 무장한 최적화된 Zsh 환경 설정. `setup.py` 한 번으로 의존성 설치부터 `.zshrc` 배포까지 자동으로 처리합니다.

## 빠른 시작

```bash
git clone <this-repo> && cd zsh
python3 setup.py
```

완료 후 터미널을 재시작하거나 `source ~/.zshrc`를 실행하세요.

## 설치 항목

`setup.py`가 순서대로 설치합니다 (이미 설치된 항목은 건너뜀):

| 단계 | 항목 | 설명 |
|------|------|------|
| 1 | Prerequisites | `zsh`, `curl`, `git` 존재 확인 |
| 2 | Oh My Zsh | Zsh 플러그인 프레임워크 |
| 3 | Powerlevel10k | 빠른 프롬프트 테마 (instant prompt 포함) |
| 4 | OMZ 커스텀 플러그인 | 아래 플러그인 목록 참고 |
| 5 | Homebrew / Linuxbrew | 크로스 플랫폼 패키지 매니저 |
| 6 | Brew 패키지 | 아래 패키지 목록 참고 |
| 7 | NVM v0.40.1 | Node.js 버전 관리 |
| 8 | Bun | 빠른 JS 런타임 및 패키지 매니저 |
| 9 | zshrc 배포 | `zshrc_best` → `~/.zshrc` (기존 파일은 `~/.zshrc.bak`으로 백업) |

### Oh My Zsh 플러그인

| 플러그인 | 기능 |
|----------|------|
| `git` | git 단축 명령어 |
| `sudo` | ESC×2로 이전 명령에 sudo 추가 |
| `extract` | 모든 압축 포맷을 `x`로 해제 |
| `copypath` | 현재 경로 클립보드 복사 |
| `colored-man-pages` | man 페이지 컬러 출력 |
| `history-substring-search` | 히스토리 부분 문자열 검색 |
| `fzf-tab` | Tab 자동완성에 fzf 적용 |
| `zsh-autosuggestions` | 히스토리 기반 인라인 제안 |
| `zsh-fzf-history-search` | Ctrl+R fzf 히스토리 검색 |
| `zsh-syntax-highlighting` | 실시간 명령어 문법 강조 |

### Brew 패키지

| 패키지 | 역할 |
|--------|------|
| `eza` | `ls` 대체 (아이콘, git 상태) |
| `bat` | `cat` 대체 (문법 강조, man 페이지) |
| `fzf` | 퍼지 파인더 |
| `fd` | `find` 대체 |
| `ripgrep` | `grep` 대체 |
| `zoxide` | `cd` 대체 (스마트 디렉토리 점프) |
| `lazygit` | 터미널 git TUI |
| `neovim` | 기본 에디터 |

## 주요 alias / 함수

### 파일 탐색

```zsh
ls   # eza --icons
ll   # eza 상세 목록 + git 상태
la   # eza 숨김 파일 포함
lt   # 트리 뷰 (2단계)
lta  # 트리 뷰 (3단계, 숨김 포함)
```

### fzf 통합

```zsh
fzp          # bat 미리보기와 함께 fzf
fv           # fzf로 파일 선택 후 nvim 열기
fkill        # fzf로 프로세스 선택 후 kill
Ctrl+T       # 파일 검색
Alt+C        # 디렉토리 검색
Ctrl+R       # 히스토리 검색
```

### Git

```zsh
lg           # lazygit
glog         # 그래프 로그
gbr          # 최근 커밋 순 브랜치 목록
gds          # git diff --stat
gpush        # 현재 브랜치를 origin에 push
gamend       # 마지막 커밋에 변경사항 추가 (메시지 유지)
gwip         # 전체 add 후 "WIP" 커밋
gunwip       # 마지막 WIP 커밋 되돌리기
```

### Python / venv

```zsh
menv         # python -m venv .venv
venv         # source .venv/bin/activate
baseenv      # ~/workspace/base 가상환경 활성화
```

### 기타

```zsh
cat          # bat (자동 감지)
grep         # ripgrep
fd           # fdfind (Debian/Ubuntu 호환)
c            # clear
reload       # source ~/.zshrc
zshrc        # nvim ~/.zshrc
```

## 요구사항

- macOS 또는 Linux
- Python 3.x
- `zsh`, `curl`, `git`

## 플랫폼 지원

- **macOS**: ARM (`/opt/homebrew`) 및 Intel (`/usr/local`) 자동 감지
- **Linux**: Linuxbrew (`/home/linuxbrew/.linuxbrew`) 자동 감지
- `bat` / `batcat` 양쪽 바이너리 이름 자동 처리 (Debian/Ubuntu)
