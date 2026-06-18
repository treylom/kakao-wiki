#!/bin/bash
# macos_osascript.sh — kakao-wiki macOS provider (GREEN)
# KakaoTalk 대화방을 GUI 자동화(osascript AX)로 텍스트 export → CSV.
#
# 출처: aktofu export-kakaotalk.sh 레시피를 *복제·일반화*(라이브 파이프라인 미수정).
#   - Kakao 전역 GUI mutex(/tmp/kakao-gui.lock) 공유 → 동시 GUI 점유 race 차단(aktofu와 직렬화).
#   - GUI 방 hard-assert + CSV 방 hard-assert(방교차 차단, 한글 NFC substring).
# KakaoTalk은 공개 API가 없어 메뉴 클릭을 osascript로 흉내냄 — osascript 의존은 macOS 전용.
#
# Usage: macos_osascript.sh "<ROOM>" "<OUT_DIR>"
# 출력(stdout 마지막 줄): 생성된 CSV 절대경로. 실패 시 비-0 exit.
set -u
ROOM="${1:?room name required}"
OUT_DIR="${2:?out dir required}"
DATE=$(date +%Y-%m-%d)
mkdir -p "$OUT_DIR"
OUT_CSV="${OUT_DIR}/${ROOM}-${DATE}.raw.csv"

log() { echo "[$(date +%H:%M:%S)] $1" >&2; }

csv_room_matches() {
  python3 -c "import sys,unicodedata,os; bn=unicodedata.normalize('NFC',os.path.basename(sys.argv[1])); name=unicodedata.normalize('NFC',sys.argv[2]); sys.exit(0 if name in bn else 1)" "$1" "$2"
}

close_extra_windows() {
  osascript -e '
  tell application "System Events"
    tell process "KakaoTalk"
      repeat 5 times
        set wCount to count of windows
        if wCount <= 2 then exit repeat
        repeat with w in every window
          set wName to name of w
          if wName is not "카카오톡" and wName is not "'"${ROOM}"'" then
            key code 53
            delay 0.3
            exit repeat
          end if
        end repeat
      end repeat
    end tell
  end tell' 2>/dev/null
  sleep 0.3
}

# Kakao 전역 mutex (aktofu와 공유) — 동시 GUI 점유 차단.
KAKAO_LOCK="/tmp/kakao-gui.lock"
if [ -d "$KAKAO_LOCK" ]; then
  LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$KAKAO_LOCK" 2>/dev/null || echo 0) ))
  [ "$LOCK_AGE" -gt 600 ] && { log "stale Kakao GUI lock(${LOCK_AGE}s) 회수"; rmdir "$KAKAO_LOCK" 2>/dev/null; }
fi
WAITED=0
while ! mkdir "$KAKAO_LOCK" 2>/dev/null; do
  if [ "$WAITED" -ge 90 ]; then
    log "Kakao GUI lock 90s 초과 — steal 후 진행(GUI/CSV assert가 race 차단)"
    rmdir "$KAKAO_LOCK" 2>/dev/null; mkdir "$KAKAO_LOCK" 2>/dev/null; break
  fi
  sleep 3; WAITED=$((WAITED+3))
done
trap 'rmdir "$KAKAO_LOCK" 2>/dev/null' EXIT
log "Kakao GUI mutex 획득"

log "Step 0: 카카오톡 활성화"
osascript -e 'tell application "KakaoTalk" to activate' 2>/dev/null
sleep 1
close_extra_windows

log "Step 1: 채팅 탭 전환"
osascript -e 'tell application "System Events" to tell process "KakaoTalk" to click button 2 of window "카카오톡"' 2>/dev/null
sleep 0.5

log "Step 2: 방 열기 — ${ROOM}"
kmsg read "${ROOM}" --limit 1 --keep-window 2>/dev/null
sleep 1

log "Step 2.5: GUI 방 hard-assert — ${ROOM}"
GUI_CHECK=$(osascript -e '
tell application "System Events"
  tell process "KakaoTalk"
    set hasTarget to "no"
    repeat with w in every window
      if name of w is "'"${ROOM}"'" then set hasTarget to "yes"
    end repeat
    return hasTarget
  end tell
end tell' 2>/dev/null)
if [ "$GUI_CHECK" != "yes" ]; then
  log "❌ GUI 방 부재: '${ROOM}' 창 미존재(방 전환 실패) → 중단(fail-fast)."
  close_extra_windows; exit 2
fi
log "✓ GUI 방 창 확인: ${ROOM}"

log "Step 3: 채팅방 설정 열기"
osascript -e '
tell application "System Events"
  tell process "KakaoTalk"
    repeat with w in every window
      if name of w is "'"${ROOM}"'" then perform action "AXRaise" of w
    end repeat
    delay 0.3
    click menu item "채팅방 설정" of menu 1 of menu bar item "채팅" of menu bar 1
  end tell
end tell' 2>/dev/null
sleep 1

log "Step 4: 대화 내용 관리 탭"
osascript -e 'tell application "System Events" to tell process "KakaoTalk" to click button 2 of window "Window"' 2>/dev/null
sleep 0.5

log "Step 5: 텍스트 파일로 저장"
osascript -e 'tell application "System Events" to tell process "KakaoTalk" to click button "텍스트 파일로 저장" of scroll area 1 of window "Window"' 2>/dev/null
sleep 2

BEFORE=$(ls -t ~/Downloads/KakaoTalk_Chat_*.csv 2>/dev/null | head -1)
BEFORE_MOD=$([ -n "$BEFORE" ] && stat -f %m "$BEFORE" || echo "0")

log "Step 6: 저장 다이얼로그 확인(Enter)"
osascript -e 'tell application "System Events" to key code 36' 2>/dev/null
sleep 3

log "Step 6.5: CSV 생성 대기(최대 600s 폴링)"
for i in $(seq 1 120); do
  sleep 5
  osascript -e 'tell application "System Events" to tell process "KakaoTalk"
    try
      click button "확인" of sheet 1 of (first window whose (count of sheets) > 0)
    end try
  end tell' 2>/dev/null
  LATEST=$(ls -t ~/Downloads/KakaoTalk_Chat_*.csv 2>/dev/null | head -1)
  [ -z "$LATEST" ] && continue
  LATEST_MOD=$(stat -f %m "$LATEST")
  [ "$LATEST_MOD" -le "$BEFORE_MOD" ] && continue
  S1=$(stat -f %z "$LATEST"); sleep 2; S2=$(stat -f %z "$LATEST")
  [ "$S1" != "$S2" ] && continue
  if ! csv_room_matches "$LATEST" "$ROOM"; then
    log "❌ CSV 방 불일치: $(basename "$LATEST") ⊉ '${ROOM}' → 중단(fail-fast)."
    osascript -e 'tell application "System Events" to key code 36' 2>/dev/null
    close_extra_windows; exit 3
  fi
  log "✓ CSV 방 확인: $(basename "$LATEST") ⊇ ${ROOM}"
  osascript -e 'tell application "System Events" to key code 36' 2>/dev/null
  sleep 1; close_extra_windows
  cp "$LATEST" "$OUT_CSV"
  log "export 성공: $OUT_CSV ($(wc -l < "$OUT_CSV") 줄)"
  echo "$OUT_CSV"
  exit 0
done

log "❌ export 실패: 600s 후 CSV 미감지"
osascript -e 'tell application "System Events" to key code 36' 2>/dev/null
close_extra_windows; exit 1
