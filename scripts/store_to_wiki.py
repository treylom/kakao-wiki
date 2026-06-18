#!/usr/bin/env python3
"""store_to_wiki.py — normalized messages JSON → Obsidian/LLM-wiki markdown note.

수집한 방 대화를 vault 노트로 저장(LLM wiki 적재). vault 노트 컨벤션 준수:
frontmatter(type/tags/aliases) + 읽기 가능한 transcript. graph_* 수동작성 ❌.

Usage:
  store_to_wiki.py --normalized <normalized.json> --vault "<ABS vault path>" \
      --subdir "Library/Research/<ROOM>" [--title "..."] [--room "..."]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from datetime import datetime


def md_escape(s: str) -> str:
    return s.replace("\n", " ").strip()


def build_note(norm: dict, room: str, title: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    msgs = norm.get("messages", [])
    head = [
        "---",
        f'title: "{title}"',
        f"date: {date}",
        "type: kakao-collection",
        f"room: \"{room}\"",
        f"tags: [kakao-wiki, kakao, collection, \"{room}\"]",
        f"aliases: [\"{room} kakao log\", \"{room} 대화 수집\"]",
        f"window: \"{norm.get('first_time','')} ~ {norm.get('last_time','')}\"",
        "stats:",
        f"  messages: {norm.get('count', 0)}",
        f"  users: {norm.get('unique_users', 0)}",
        "okf_type: Dataset",
        "---",
        "",
        f"# {title}",
        "",
        f"> kakao-wiki 수집 노트 · 방 **{room}** · "
        f"{norm.get('count',0)}건 · 참여자 {norm.get('unique_users',0)}명 · "
        f"{norm.get('first_time','')} ~ {norm.get('last_time','')}",
        f"> 출처 export: `{norm.get('source','')}` · 봇/공지 제외 {norm.get('filtered_bot_announcement',0)}건",
        "",
        "관련: [[kakao-wiki]] 수집 스킬로 생성. 분석·인용 검증은 aktofu citation_gate 재사용.",
        "",
        "## 대화 기록",
        "",
    ]
    body = []
    for m in msgs:
        t = (m.get("time") or "")[11:16] if len(m.get("time") or "") >= 16 else (m.get("time") or "")
        u = m.get("user", "")
        body.append(f"- **[{t}] {u}**: {md_escape(m.get('msg',''))}")
    return "\n".join(head + body) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalized", required=True)
    ap.add_argument("--vault", required=True, help="vault 루트 절대경로")
    ap.add_argument("--subdir", required=True, help="vault 루트 기준 상대 폴더")
    ap.add_argument("--room", default="")
    ap.add_argument("--title", default="")
    a = ap.parse_args()

    norm = json.loads(Path(a.normalized).read_text(encoding="utf-8"))
    room = a.room or Path(a.normalized).name.split("-")[0]
    date = datetime.now().strftime("%Y-%m-%d")
    title = a.title or f"[{date}] {room} 카톡 수집"

    vault = Path(a.vault)
    if not vault.is_absolute():
        print("ERROR: --vault 는 절대경로여야 함 (vault-ops §4)", file=sys.stderr)
        return 1
    dest_dir = vault / a.subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{room}-{date}.md"
    dest.write_text(build_note(norm, room, title), encoding="utf-8")
    print(str(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
