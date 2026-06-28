# OpenCode 폐쇄망 배포 가이드

## 목적

opencode 바이너리 + 플러그인 + 런타임을 하나의 번들로 묶어, 폐쇄망에서 여러 사용자가 개별 `npm install` 없이 즉시 사용할 수 있도록 한다.

---

## 디렉토리 구조

```
/opt/opencode-deploy/
├── bin/
│   └── opencode                    # opencode 바이너리 (버전 고정)
├── runtimes/
│   └── node/
│       └── bin/node                # Node.js 런타임 (버전 고정)
├── config/
│   ├── opencode.jsonc              # 플러그인 선언 (버전 고정)
│   ├── package.json                # @opencode-ai/plugin 버전 고정
│   ├── package-lock.json
│   └── node_modules/               # npm install 완료 → 통째로 배포
│       ├── @opencode-ai/
│       │   └── plugin/
│       └── oh-my-openagent/
│           └── ...
├── activate.sh                     # 사용자 환경 설정 스크립트
└── VERSION                         # 번들 버전 파일
```

### config/ 구조 상세 (OpenCode가 실제로 읽는 부분)

```
config/
├── opencode.jsonc      ← OPENCODE_CONFIG_DIR이 가리키는 경로
├── package.json        ← @opencode-ai/plugin 버전 명시
├── node_modules/
│   ├── @opencode-ai/plugin/    ← plugin SDK (opencode 버전과 짝 맞춤)
│   └── oh-my-openagent/       ← oh-my-openagent plugin
│       └── node_modules/...   ← oh-my-openagent 자체 의존성
```

---

## 환경변수

| 변수 | 값 | 설명 |
|---|---|---|
| `OPENCODE_CONFIG_DIR` | `/opt/opencode-deploy/config` | **핵심.** opencode가 config, node_modules, plugin을 찾는 기준 경로 |
| `PATH` | `...:/opt/opencode-deploy/bin:/opt/opencode-deploy/runtimes/node/bin` | opencode 바이너리 + Node.js 런타임 |

### opencode config 우선순위 (낮음 → 높음)

1. `/etc/opencode/opencode.json` — 시스템 전역 managed config
2. `~/.config/opencode/opencode.json` — 사용자 글로벌 config
3. **`$OPENCODE_CONFIG_DIR/opencode.jsonc`** ← 여기에 플러그인 선언
4. `$OPENCODE_CONFIG/env:OPENCODE_CONFIG` — 개별 config 파일 오버라이드
5. `{project}/opencode.json` — 프로젝트 config (최우선)

> 폐쇄망 배포에서는 `OPENCODE_CONFIG_DIR`이 주가 되고, 각 사용자의 `~/.config/opencode/` 는 건드리지 않음.

---

## `activate.sh`

```bash
#!/bin/bash
# OpenCode 배포 환경 설정
# 사용법: source /opt/opencode-deploy/activate.sh

export OPENCODE_CONFIG_DIR="/opt/opencode-deploy/config"
export PATH="/opt/opencode-deploy/bin:/opt/opencode-deploy/runtimes/node/bin:$PATH"

echo "[OK] OpenCode deployment environment ready"
echo "     Config: $OPENCODE_CONFIG_DIR"
echo "     Run: opencode tui"
```

사용자는 `source activate.sh` 한 줄이면 끝. 각 계정의 `.bashrc`에 넣어도 됨.

---

## `opencode.jsonc`

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["oh-my-openagent@1.3.0"]
  // @latest 사용 금지 — pack step에서 실제 버전으로 치환
}
```

---

## 배포 번들 생성 (Pack 스크립트)

인터넷이 되는 **빌드 서버**에서 실행:

```bash
#!/bin/bash
# pack.sh — 배포 번들 생성
set -euo pipefail

BUNDLE_VERSION="${1:-$(date +%Y%m%d)}"
DIST="dist/opencode-deploy-v${BUNDLE_VERSION}"

echo "=== OpenCode Deploy Bundle v${BUNDLE_VERSION} ==="

# 0. 준비
rm -rf "$DIST"
mkdir -p "$DIST/config"

# 1. opencode.jsonc
cp opencode.jsonc "$DIST/config/opencode.jsonc"

# 2. package.json
cat > "$DIST/config/package.json" <<EOF
{
  "private": true,
  "dependencies": {
    "@opencode-ai/plugin": "1.17.9"
  }
}
EOF

# 3. npm install
cd "$DIST/config"
npm install
cd -

# 4. oh-my-openagent를 node_modules에 직접 설치
cd "$DIST/config"
npm install oh-my-openagent@latest --save
cd -

# 5. @latest → 실제 버전 치환 (중요!)
OMO_VER=$(node -e "console.log(require('./dist/config/node_modules/oh-my-openagent/package.json').version)")
sed -i "s/oh-my-openagent@latest/oh-my-openagent@$OMO_VER/" "$DIST/config/opencode.jsonc"

# 6. opencode 바이너리 + Node.js 복사
cp /path/to/opencode-binary "$DIST/bin/opencode"
cp -r /path/to/node-runtime "$DIST/runtimes/node"

# 7. activate.sh
cp activate.sh "$DIST/activate.sh"
echo "$BUNDLE_VERSION" > "$DIST/VERSION"

# 8. tarball 생성
cd dist
tar czf "opencode-deploy-v${BUNDLE_VERSION}.tar.gz" "opencode-deploy-v${BUNDLE_VERSION}/"
echo "=== Done: dist/opencode-deploy-v${BUNDLE_VERSION}.tar.gz ==="
```

---

## 사용자 측 설치

```bash
# 1. 관리자가 tarball 배포 (USB / 내부망)
# 2. 공용 경로에 압축 풀기
sudo tar xzf opencode-deploy-v20260624.tar.gz -C /opt/
# 3. 환경 설정 (각 계정 .bashrc에 추가)
echo 'source /opt/opencode-deploy/activate.sh' >> ~/.bashrc
# 4. 실행
source ~/.bashrc
opencode tui
```

---

## 버전 호환성 매트릭스

| 번들 버전 | opencode 버전 | @opencode-ai/plugin | oh-my-openagent | Node.js |
|---|---|---|---|---|
| v20260624 | 1.17.9 | 1.17.9 | 1.3.0 | 22.x |
| v20260701 | 1.18.0 | 1.18.0 | 1.4.0 | 22.x |

관리자가 직접 검증 후 번들 버전을 올림. 사용자는 번들만 다시 받으면 됨.

---

## 주의사항

| 항목 | 내용 |
|---|---|
| `@latest` 금지 | registry 조회 시도 → 폐쇄망에서 타임아웃. **pack step에서 반드시 고정 버전으로 치환** |
| 사용자 `npm install` 금지 | 사용자 계정에서 `npm install` 실행 시 `OPENCODE_CONFIG_DIR/node_modules` symlink 깨질 수 있음 |
| `opencode update` 금지 | 폐쇄망에서 실행 시 실패. 새 버전은 번들을 다시 받아야 함 |
| 권한 | `/opt/opencode-deploy/`는 `755` (모든 사용자 읽기/실행 가능) |
