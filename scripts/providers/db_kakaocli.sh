#!/bin/bash
# db_kakaocli.sh — kakao-wiki DB-direct provider (⚠️ EXPERIMENTAL)
#
# GUI 자동화(osascript/pywinauto)를 완전 우회하고 KakaoTalk 로컬 DB 를 직접 읽는다.
# 가장 견고(요소 트리 fragility 0)하지만 kakaocli 키유도가 호스트에서 성공해야 동작.
#   - macOS: kakaocli auth(키유도+DB접근 검증) → kakaocli messages/query 로 방 메시지 읽기.
#   - Windows: DB 스키마·키유도가 Mac 과 다를 수 있어 별도 검증 필요(연구 §2.3, ⚪ 불확실).
#
# Usage: db_kakaocli.sh "<ROOM>" "<OUT_DIR>"
# 출력(stdout 마지막 줄): 생성된 CSV 경로. kakaocli 미가용/키유도 실패 시 비-0 exit.
#
# ⚠️ kakaocli 바이너리 경로는 환경별 상이 — KAKAOCLI 환경변수로 주입 가능.
set -u
ROOM="${1:?room name required}"
OUT_DIR="${2:?out dir required}"
DATE=$(date +%Y-%m-%d)
mkdir -p "$OUT_DIR"
OUT_CSV="${OUT_DIR}/${ROOM}-${DATE}.raw.csv"

KAKAOCLI="${KAKAOCLI:-kakaocli}"
command -v "$KAKAOCLI" >/dev/null 2>&1 || {
  # local build fallback (if present)
  for c in \
    "./kakaocli" \
    "./.build/release/kakaocli"; do
    [ -x "$c" ] && KAKAOCLI="$c" && break
  done
}
command -v "$KAKAOCLI" >/dev/null 2>&1 || [ -x "$KAKAOCLI" ] || {
  echo "EXPERIMENTAL: kakaocli 미발견 (KAKAOCLI 환경변수로 경로 지정). DB 경로 사용 불가." >&2
  exit 5
}

echo "[db] auth(키유도+DB접근 검증)…" >&2
"$KAKAOCLI" auth >/dev/null 2>&1 || {
  echo "EXPERIMENTAL: kakaocli auth 실패(키유도 불가) — 호스트 DB 접근 미지원. GUI provider 사용 권장." >&2
  exit 6
}

echo "[db] messages 추출 — ${ROOM}" >&2
# kakaocli messages 는 방 이름으로 최근 메시지를 출력. CSV 정합(YYYY-MM-DD HH:MM:SS,user,msg)은
# kakaocli 출력 포맷에 따라 후처리 필요 — 환경별 포맷 확정 후 매핑(EXPERIMENTAL).
# 안전 동작: 추출 성공 시 CSV 로 저장, 포맷 불확정이면 raw 덤프 + 경고.
if "$KAKAOCLI" messages --chat "$ROOM" --csv > "$OUT_CSV" 2>/dev/null && [ -s "$OUT_CSV" ]; then
  echo "[db] export: $OUT_CSV ($(wc -l < "$OUT_CSV") 줄)" >&2
  echo "$OUT_CSV"
  exit 0
fi
echo "EXPERIMENTAL: kakaocli messages --csv 미지원/실패 — 출력 포맷 확정 후 매핑 필요(references)." >&2
exit 7
