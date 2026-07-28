#!/usr/bin/env python3
"""normalize.py — KakaoTalk export(CSV or txt) → normalized messages JSON.

GUI 무관 순수 파서. aktofu step2-analyze.py 의 파싱·봇/공지 필터를 *복제·일반화*
(토픽 분석은 제외 — 본 스킬은 범용 수집이라 normalized 메시지까지만 생성).

Usage:
  normalize.py --raw <export.csv|export.txt> --out <normalized.json> [--since "YYYY-MM-DD HH:MM:SS"]
"""
from __future__ import annotations
import argparse, csv, json, re, sys, unicodedata
from pathlib import Path

# 오픈채팅 봇 발화 / 입퇴장·시스템 공지 = 수집 제외 (aktofu P1 동일).
BOT_SENDERS = {"opencrab", "오픈크랩", "오픈크랩봇", "방봇", "open crab", "오픈채팅봇"}
ANNOUNCE_RE = re.compile(
    r"(님이\s*(들어왔|나갔|입장|퇴장)|님을\s*내보냈|방장.{0,6}(위임|변경|되셨|넘)|"
    r"채팅방\s*(관리자|공지|입장)|운영\s*정책|신고가\s*접수|^\s*\[(공지|안내|입장|퇴장)\])"
)


def is_bot_or_announcement(user: str, msg: str) -> bool:
    return user.strip().lower() in BOT_SENDERS or bool(ANNOUNCE_RE.search(msg))


def parse_csv_rows(path: Path):
    """KakaoTalk CSV: row[0]=YYYY-MM-DD HH:MM:SS, row[1]=user, row[2..]=msg."""
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            next(reader)  # header
        except StopIteration:
            return
        for row in reader:
            if len(row) < 3:
                continue
            dt, user = row[0], row[1]
            msg = ",".join(row[2:]) if len(row) > 3 else row[2]
            yield dt, user, msg


# KakaoTalk Windows txt export 라인: "2026. 6. 18. 오후 8:19, 홍길동 : 메시지"
# 2026-06-25 KST WSL2/Windows spike 기준. Header lines like "저장한 날짜 :" are skipped.
TXT_WINDOWS_LINE_RE = re.compile(
    r"^(?P<year>\d{4})\.\s*(?P<month>\d{1,2})\.\s*(?P<day>\d{1,2})\.\s*"
    r"(?P<ampm>오전|오후)\s*(?P<hour>\d{1,2}):(?P<minute>\d{2}),\s*"
    r"(?P<user>.+?)\s*:\s*(?P<msg>.*)$"
)
# KakaoTalk PC(Ctrl+S) txt export 라인: "[홍길동] [오후 8:19] 메시지"
# 날짜는 라인에 없고 구분선("--------------- 2026년 7월 28일 월요일 ---------------")이 공급.
TXT_PC_LINE_RE = re.compile(
    r"^\[(?P<user>[^\]]{1,40})\]\s*\[(?P<ampm>오전|오후)\s*(?P<hour>\d{1,2}):(?P<minute>\d{2})\]\s?(?P<msg>.*)$"
)
TXT_DATE_HEADER_RE = re.compile(
    r"(?P<year>\d{4})년\s*(?P<month>\d{1,2})월\s*(?P<day>\d{1,2})일"
)
TXT_LINE_RE = re.compile(r"^\[?(?P<user>[^\]:,]{1,40})[\]]?\s*[,:]\s*(?P<rest>.+)$")


def _windows_dt(match: re.Match) -> str:
    hour = int(match.group("hour"))
    if match.group("ampm") == "오후" and hour != 12:
        hour += 12
    if match.group("ampm") == "오전" and hour == 12:
        hour = 0
    return (
        f"{int(match.group('year')):04d}-{int(match.group('month')):02d}-"
        f"{int(match.group('day')):02d} {hour:02d}:{int(match.group('minute')):02d}:00"
    )


def _pc_dt(cur_date: str, match: re.Match) -> str:
    hour = int(match.group("hour"))
    if match.group("ampm") == "오후" and hour != 12:
        hour += 12
    if match.group("ampm") == "오전" and hour == 12:
        hour = 0
    hm = f"{hour:02d}:{int(match.group('minute')):02d}:00"
    return f"{cur_date} {hm}" if cur_date else ""


def parse_txt_rows(path: Path):
    """KakaoTalk txt export — Windows/PC(Ctrl+S) formats first, then legacy fallback.

    PC(Ctrl+S) 포맷은 라인에 날짜가 없어 날짜 구분선을 상태로 유지하고,
    어떤 패턴에도 안 걸리는 라인은 직전 메시지의 연속(멀티라인)으로 병합한다.
    """
    cur_date = ""       # PC 포맷용 현재 날짜 (YYYY-MM-DD)
    pending = None      # 직전 메시지 [dt, user, msg] — 멀티라인 병합 대상
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.rstrip()
        if not line:
            continue
        # 날짜/저장 정보 헤더 라인 스킵
        if line.startswith(("저장한 날짜", "채팅방 이름", "대화 상대")) or "님과 카카오톡 대화" in line:
            continue
        # 날짜 구분선/단독 날짜 라인 → 현재 날짜 갱신 (메시지 아님)
        dm = TXT_DATE_HEADER_RE.search(line)
        if dm and not TXT_WINDOWS_LINE_RE.match(line) and not TXT_PC_LINE_RE.match(line):
            cur_date = f"{int(dm.group('year')):04d}-{int(dm.group('month')):02d}-{int(dm.group('day')):02d}"
            continue
        wm = TXT_WINDOWS_LINE_RE.match(line)
        if wm:
            if pending:
                yield tuple(pending)
            pending = [_windows_dt(wm), wm.group("user").strip(), wm.group("msg").strip()]
            continue
        pm = TXT_PC_LINE_RE.match(line)
        if pm:
            if pending:
                yield tuple(pending)
            pending = [_pc_dt(cur_date, pm), pm.group("user").strip(), pm.group("msg").strip()]
            continue
        m = TXT_LINE_RE.match(line)
        if m:
            if pending:
                yield tuple(pending)
            pending = ["", m.group("user").strip(), m.group("rest").strip()]
            continue
        # 어떤 패턴에도 안 걸림 → 직전 메시지의 연속 라인(멀티라인 메시지)
        if pending:
            pending[2] = pending[2] + "\n" + line
    if pending:
        yield tuple(pending)


def normalize(raw: Path, since: str | None):
    rows = parse_csv_rows(raw) if raw.suffix.lower() == ".csv" else parse_txt_rows(raw)
    messages, users, filtered = [], set(), 0
    since_n = since.strip() if since else ""
    for dt, user, msg in rows:
        if since_n and dt and dt <= since_n:
            continue
        if is_bot_or_announcement(user, msg):
            filtered += 1
            continue
        messages.append({"time": dt, "user": user, "msg": msg})
        users.add(user)
    return {
        "schema_version": "1",
        "proof_class": "in-process",
        "source": str(raw),
        "count": len(messages),
        "unique_users": len(users),
        "filtered_bot_announcement": filtered,
        "first_time": messages[0]["time"] if messages else "",
        "last_time": messages[-1]["time"] if messages else "",
        "messages": messages,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--since", default="")
    a = ap.parse_args()
    raw = Path(a.raw)
    if not raw.exists():
        print(f"ERROR: raw not found: {raw}", file=sys.stderr)
        return 1
    norm = normalize(raw, a.since or None)
    Path(a.out).write_text(json.dumps(norm, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"normalized: {norm['count']} messages, {norm['unique_users']} users "
          f"({norm['first_time']} ~ {norm['last_time']}) -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
