# kakao-wiki

**카카오톡** 채팅방 대화를 구조화된 노트로 만들어 내 옵시디언 / LLM 위키 저장소에 쌓고, 필요하면 요약을 다시 카카오톡·디스코드·슬랙으로 보내는 스킬입니다.

(English README: [README.en.md](README.en.md))

하는 일은 하나로 추상화돼 있습니다:

```
collect(방) → 정규화(normalize) → 저장소에 저장   (+ 선택: send(채널, 메시지))
```

카카오톡은 공개 API가 없어서, 수집은 카카오톡 앱 자체의 **대화 내보내기(export) 메뉴**를 자동으로 구동합니다. 그 뒤의 파싱·저장·다채널 발송은 결정론적(deterministic) 파이썬입니다.

> 이 도구를 어떻게 쓰고 어떤 데이터를 모으는지는 사용자 본인의 책임입니다.

---

## 한눈에 — provider(수집 백엔드)별 상태 (정직하게)

이 저장소는 모든 경로가 다 된다고 포장하지 않습니다. 각 provider가 스스로 자기 상태를 표시합니다.

| provider | 하는 일 | OS | 상태 |
|----------|---------|----|------|
| `macos` (기본) | 카카오톡 GUI 내보내기 메뉴를 `osascript`(접근성)로 구동 → CSV 파싱 | macOS | ✅ **검증됨(GREEN)** — 실제 export 1회로 검증 (`references/macos-provider.md`) |
| `windows` | `pywinauto`로 `Ctrl+S` 로컬 txt 저장 | Windows | ⚠️ **검증 대기(spike-pending)** — 셀렉터 비의존 로직은 구현 완료, **실제 윈도우 카카오톡 검증 전까지 성공을 가장하지 않음**(기본 비-0 종료) |
| `db` | 로컬 카카오톡 DB를 `kakaocli`로 직접 읽기 | macOS(Win 미정) | 🧪 **실험적** — 호스트에서 `kakaocli` 키 유도가 성공해야 동작 |

지금 바로 쓰려면 `macos` 경로를 쓰세요. `windows`/`db`는 **숨기지 않고 표시**해 둔 미완성 경로입니다(기여 환영).

---

## 준비물

- **Python 3.9+** (핵심 흐름은 표준 라이브러리만 — 별도 설치 불필요)
- **macOS provider**: 카카오톡 데스크톱 앱 + `kmsg`(`/opt/homebrew/bin/kmsg`) + 카카오톡·`kmsg`·터미널에 **접근성 권한** 부여 (시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용)
- **PDF 등 문서 변환을 같이 쓸 때**: `kordoc` + `pdfjs-dist@4` (아래 "문서 변환" 참고)
- **send.py**: `DISCORD_BOT_TOKEN`(디스코드) / Slack MCP(슬랙) / `kmsg`(카카오톡) — 보낼 때만 필요

---

## 설치

```bash
git clone https://github.com/treylom/kakao-wiki.git
cd kakao-wiki
# 핵심 흐름은 의존성 0. (윈도우 provider만 선택적으로: pip install pywinauto)
```

또는 Claude Code / 에이전트 스킬 폴더에 `kakao-wiki` 스킬로 넣어 쓸 수 있습니다(`SKILL.md` 참고).

---

## 사용법

`ROOM` = 정확한 카카오톡 방 이름, `OUT` = 작업 폴더.

### 1. 수집
```bash
# macOS (기본, 검증됨):
python3 scripts/collect.py --room "<ROOM>" --provider macos --out ./out
```
→ `out/<ROOM>-<DATE>.raw.csv` 와 `out/<ROOM>-<DATE>.normalized.json` 생성.

### 2. 저장소에 저장
```bash
python3 scripts/store_to_wiki.py \
  --normalized out/<ROOM>-<DATE>.normalized.json \
  --vault "/내/저장소/절대경로" \
  --subdir "Research/<ROOM>"
```
→ 프론트매터(`type`·`tags`·`aliases`·통계) 붙은 마크다운 노트 생성.

### 3. (선택) 요약 발송
```bash
python3 scripts/send.py --channel kakao   --room "<ROOM>"        --message-file summary.txt
python3 scripts/send.py --channel discord --target <channel_id> --message-file summary.txt
python3 scripts/send.py --channel slack   --target "<#channel>" --message-file summary.txt
```
`send.py`는 *인터페이스*만 통일합니다. 실제 전송 방식은 채널마다 다릅니다(kmsg / 디스코드 REST / 슬랙 MCP — `references/send-channels.md`).

---

## 무인 수집 (Windows ⓐ — 설계됨, 실측 대기)

Windows에서 사람 개입 0으로 수집(자동 로그인 + 방 자동오픈 + export)하려면:

```bash
# 1) 자격증명을 로컬에 설정 (절대 커밋 금지 — .gitignore 처리됨)
#    환경변수:  set KW_KAKAO_ID=...  &  set KW_KAKAO_PW=...
#    또는 레포 밖 파일:  ~/.kakao-wiki/credentials.env  (KW_KAKAO_ID= / KW_KAKAO_PW=)
# 2) 무인 실행
python scripts/providers/windows_pywinauto.py --room "<ROOM>" --out ./out \
  --unattended --i-have-verified-on-real-windows
```

- **자격증명은 사용자 소유**: ID/PW는 *본인이 로컬에 직접* 설정합니다. 공개 레포에 비밀번호를 저장하지 않으며, 비밀번호는 카카오톡 입력창에만 들어가고 화면·로그 어디에도 표시되지 않습니다(`scripts/providers/_credentials.py`).
- **상태**: 자격증명 레이어는 완성·검증됨. 로그인/검색 UI 자동화는 실제 윈도우 카카오톡 spike로 셀렉터를 확정한 뒤 GREEN 승격(`references/windows-provider-spike.md`).

> ⚠️ **단일 세션 제약(카카오톡 플랫폼)**: 카카오톡은 한 계정이 한 기기에서만 로그인됩니다. 무인 수집이 로그인하는 순간 다른 기기(폰 등)의 카카오톡 세션이 끊깁니다. *수집이 도는 동안만* 이 PC가 세션을 가져가고 안 돌 땐 다른 기기로 자유롭게 쓰는 모델로 운영하세요. 도구 결함이 아니라 카카오톡 자체 제약입니다.

---

## 요약 스타일 선택 (사용자 커스텀)

발송할 요약의 **말투·형식을 골라** 쓸 수 있습니다. 환경을 감지해 자동으로 적절한 방법을 씁니다:

- **`/prompt` 스킬이 있는 환경**이면 그 스킬로 요약 프롬프트를 생성합니다.
- 없으면 **번들된 프리셋**(`prompts/summary-styles.md`)에서 고릅니다 — 예: `brief`(간결 3줄) · `detailed`(상세) · `bullets`(불릿) · `formal`(존댓말 보고체) · `casual`(편한 말투).

```bash
# 프리셋 목록 보기
python3 scripts/summarize.py --list
# 스타일 골라 요약 프롬프트 출력(요약 LLM에 그대로 전달)
python3 scripts/summarize.py --style brief --normalized out/<ROOM>-<DATE>.normalized.json
```
자세한 건 `prompts/summary-styles.md` 와 `SKILL.md`("요약 스타일") 참고.

---

## 문서 변환 (선택 — kordoc 연계)

수집한 첨부/문서가 **HWP·HWPX·복잡한 표 XLSX/DOCX·한국어 PDF**처럼 그냥 못 읽는 형식이면 [kordoc](https://github.com/chrisryugj/kordoc)으로 md 변환 후 쓸 수 있습니다.

⚠️ **PDF는 `pdfjs-dist@4` 가 kordoc 과 같은 `node_modules` 에 있어야 합니다**(v6 비호환). `npx -y kordoc <pdf>` 단독은 PDF에서 실패하니, PDF를 쓸 땐 한 번만:
```bash
mkdir kordoc-tmp && cd kordoc-tmp && npm init -y && npm install kordoc pdfjs-dist@4
./node_modules/.bin/kordoc <파일>.pdf -d ./out
# HWPX/DOCX/XLSX 만이면 추가 설치 없이: npx -y kordoc <파일>.hwpx -d ./out
```

---

## 수집 원리 (macOS)

카카오톡은 내보내기가 GUI 메뉴뿐이라, `macos_osascript.sh`가 사람이 클릭하는 순서를 접근성으로 재현합니다. **엉뚱한 방을 수집하지 않도록** 두 단계 검증을 넣었습니다:

1. 앱 포커스 → 채팅 탭 → 대상 방 열기
2. **GUI 방 검증** — 내보내기 전에 방 창이 실제로 있는지 확인
3. 설정 → 대화 내용 관리 → "텍스트 파일로 저장" → 확인
4. **CSV 방 검증** — 나온 CSV가 정말 대상 방 것인지 확인(한글 NFC substring), 아니면 즉시 실패(fail-fast)

전역 잠금(`/tmp/kakao-gui.lock`)으로 동시 실행을 직렬화합니다. 셀렉터는 카카오톡 macOS UI(창 이름·버튼 인덱스·메뉴 텍스트)에 의존하므로, 앱 UI가 바뀌면 셀렉터를 다시 잡아야 합니다(검증 단계가 조용한 오수집 대신 큰 소리로 실패).

---

## 폴더 구조

```
kakao-wiki/
  SKILL.md                  # 스킬 매니페스트(에이전트 로드용)
  scripts/
    collect.py              # provider 디스패치: collect(방, provider) -> normalized.json
    normalize.py            # raw export(CSV/txt) -> 정규화 메시지(GUI 무관 파서)
    store_to_wiki.py        # normalized -> 저장소 마크다운 노트
    summarize.py            # 요약 스타일 선택(/prompt 감지 + 프리셋)
    send.py                 # send(채널, 메시지): kakao | discord | slack
    providers/
      macos_osascript.sh    # 검증됨: 카카오톡 GUI export -> CSV (mutex + 방 검증)
      windows_pywinauto.py  # 검증대기: Ctrl+S export + 무인(ⓐ) 로그인·방오픈 골격 (셀렉터 ENV)
      _credentials.py       # ⓐ 자격증명 로딩 (로컬 ID/PW, 비밀번호 비노출 — 미커밋)
      db_kakaocli.sh        # 실험적: kakaocli DB read -> CSV
  prompts/
    summary-styles.md       # 요약 스타일 프리셋 프롬프트
  references/
    architecture.md         # provider 추상화 + 데이터 흐름 + 윈도우 현실성 등급
    macos-provider.md       # osascript 의존 지점 + 검증 로그
    windows-provider-spike.md  # Ctrl+S scaffold + 스파이크 체크리스트
    send-channels.md        # kmsg(카카오) / 디스코드(REST) / 슬랙(MCP)
```

---

## 기여

가장 값진 기여는 **윈도우 provider 스파이크 완성**(`references/windows-provider-spike.md`에 무엇을 검증해야 하는지 정리)과 **db provider 강화**입니다. 정직 원칙을 지켜주세요 — 실제 머신에서 검증되기 전까지 어떤 provider도 "검증됨(GREEN)"으로 표시하지 않습니다.

## 라이선스

MIT — [LICENSE](LICENSE) 참고.
