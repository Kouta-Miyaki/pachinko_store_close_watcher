#!/usr/bin/env python3
"""p-johojima.jp の閉店カテゴリRSSを監視し、新着記事があればDiscordへ通知する。

- 外部依存なし（Python標準ライブラリのみ）
- 既読の記事URLを state.json に保存して差分を判定する
- 初回実行時は既存記事を「既読」として記録するだけで通知はしない（過去記事の大量通知を防ぐ）
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = "https://p-johojima.jp/category/close/feed/"
STATE_FILE = Path(__file__).with_name("state.json")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
USER_AGENT = "pachinko-close-watcher/1.0 (+https://github.com)"
# state.json に保存する既読URLの上限（無限肥大化を防ぐ）
MAX_STATE_ENTRIES = 300


def fetch_feed() -> str:
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_items(xml_text: str) -> list[dict]:
    """RSSのitemを新しい順（フィード掲載順）で返す。"""
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if link:
            items.append({"title": title, "link": link, "pubDate": pub_date})
    return items


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"seen": []}


def save_state(seen_links: list[str]) -> None:
    data = {"seen": seen_links[:MAX_STATE_ENTRIES]}
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def send_discord(item: dict) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URL 未設定のため通知をスキップ:", item["link"])
        return
    payload = {
        "username": "閉店情報bot",
        "embeds": [
            {
                "title": item["title"][:256] or "新着記事",
                "url": item["link"],
                "description": item["pubDate"],
                "color": 0xE74C3C,
            }
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 300:
            print(f"[WARN] Discord応答コード {resp.status}: {item['link']}")


def main() -> int:
    try:
        xml_text = fetch_feed()
        items = parse_items(xml_text)
    except Exception as exc:  # ネットワークや解析失敗時は終了コード1
        print(f"[ERROR] フィード取得/解析に失敗: {exc}", file=sys.stderr)
        return 1

    if not items:
        print("[WARN] フィードに記事が見つかりませんでした")
        return 0

    state = load_state()
    seen = set(state.get("seen", []))
    current_links = [it["link"] for it in items]

    if not seen:
        # 初回: 既存記事を既読として記録するだけ（通知しない）
        save_state(current_links)
        print(f"初回実行: {len(current_links)}件を既読として記録しました（通知なし）")
        return 0

    # 新着 = まだ既読にないもの。古い順に通知してDiscordで新しいものが下に来るようにする
    new_items = [it for it in items if it["link"] not in seen]
    for it in reversed(new_items):
        print("新着:", it["title"], it["link"])
        send_discord(it)

    if new_items:
        # 現在のフィード + 既存の既読 を結合して保存（新しい順を維持）
        merged = current_links + [l for l in state.get("seen", []) if l not in current_links]
        save_state(merged)
        print(f"{len(new_items)}件の新着を通知し、state.jsonを更新しました")
    else:
        print("新着はありませんでした")

    return 0


if __name__ == "__main__":
    sys.exit(main())
