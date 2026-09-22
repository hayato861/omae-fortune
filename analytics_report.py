from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone


DEFAULT_SERVICE_ID = "srv-dadnjngu01pc73bj9tag"
REQUEST_PATTERN = re.compile(r'"(GET|POST) ([^ ?"]+)(?:\?[^ "]*)? HTTP/[^"]+" (\d{3})')


def parse_json_stream(raw: str) -> list[dict]:
    decoder = json.JSONDecoder()
    records = []
    position = 0
    while position < len(raw):
        while position < len(raw) and raw[position].isspace():
            position += 1
        if position >= len(raw):
            break
        record, position = decoder.raw_decode(raw, position)
        records.append(record)
    return records


def summarize(records: list[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        message = record.get("message", "")
        try:
            payload = json.loads(message)
        except (ValueError, TypeError):
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("event"), str):
            counts[payload["event"]] += 1

        request = REQUEST_PATTERN.search(message)
        if not request:
            continue
        method, path, status = request.groups()
        if status.startswith(("2", "3")):
            if method == "GET" and path == "/":
                counts["server_top_requests"] += 1
            elif method == "POST" and path == "/fortune":
                counts["fortune_requests"] += 1
            elif method == "GET" and path == "/premium":
                counts["premium_views"] += 1
    if "page_view" in counts:
        counts["page_views"] = counts.pop("page_view")
    elif "server_top_requests" in counts:
        counts["page_views"] = counts["server_top_requests"]
    counts.pop("server_top_requests", None)
    if "pages_fortune_completed" in counts:
        counts["fortune_completed"] += counts["pages_fortune_completed"]
    return dict(counts)


def fetch_event_logs(service: str, start: str, end: str) -> list[dict]:
    """Exclude health checks and page backward without truncating at 1,000 logs."""
    records = {}
    while True:
        command = [
            "render", "logs", "--resources", service, "--start", start, "--end", end,
            "--text", "event", "--direction", "backward", "--limit", "1000", "--output", "json",
        ]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        batch = parse_json_stream(result.stdout)
        previous_size = len(records)
        for record in batch:
            records[record["id"]] = record
        if len(batch) < 1000:
            return list(records.values())
        oldest = min(record["timestamp"] for record in batch)
        if oldest == end or len(records) == previous_size:
            raise RuntimeError("ログが同一時刻に集中しています。期間を短くして再集計してください。")
        # Keep Render's nanosecond precision; inclusive boundary IDs are deduplicated.
        end = oldest


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderログから初期反応を集計します")
    parser.add_argument("--hours", type=int, default=24, help="何時間前まで集計するか（既定: 24）")
    parser.add_argument("--service", default=DEFAULT_SERVICE_ID, help="Render service ID")
    args = parser.parse_args()

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=max(1, args.hours))
    counts = summarize(fetch_event_logs(args.service, start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")))

    labels = (
        ("page_views", "サイト閲覧（PV）"),
        ("landing_view", "鑑定入口表示"),
        ("fortune_started", "鑑定開始"),
        ("fortune_completed", "鑑定完了"),
        ("pages_fortune_completed", "うちPages内完了"),
        ("share_started", "共有操作"),
        ("share_completed", "共有完了"),
        ("fortune_helpful", "刺さった"),
        ("fortune_missed", "見当違い"),
        ("premium_clicked", "極み版クリック"),
    )
    print(f"直近 {args.hours} 時間")
    for key, label in labels:
        print(f"{label:<12} {counts.get(key, 0):>6}")
    print("※取得できたログ内のイベント回数です。人数ではありません。計測開始前・保存期限外・送信失敗分は含みません。")

    views = counts.get("landing_view", 0)
    completed = counts.get("fortune_completed", 0)
    shared = counts.get("share_completed", 0)
    if views:
        print(f"鑑定完了率      {completed / views:>6.1%}")
        print(f"共有完了率      {shared / views:>6.1%}")


if __name__ == "__main__":
    main()
