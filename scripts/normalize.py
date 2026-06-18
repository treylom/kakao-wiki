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


# KakaoTalk Windows txt export 라인: "2026. 6. 18. 오후 8:19, 홍길동 : 메시지" 형태 변형 다수.
# 보편 패턴 1종 + fallback. (Windows 실 export 포맷은 spike 시 확정 — references/windows-provider-spike.md)
TXT_LINE_RE = re.compile(r"^\[?(?P<user>[^\]:,]{1,40})[\]]?\s*[,:]\s*(?P<rest>.+)$")


def parse_txt_rows(path: Path):
    """범용 txt fallback — 라인 단위. (Windows export 포맷 확정 전 best-effort, spike-pending)"""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.rstrip()
        if not line:
            continue
        # 날짜 헤더 라인 스킵
        if re.match(r"^\d{4}[.\-/]", line) and "," not in line:
            continue
        m = TXT_LINE_RE.match(line)
        if not m:
            continue
        yield "", m.group("user").strip(), m.group("rest").strip()


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
