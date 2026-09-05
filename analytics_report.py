from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone


DEFAULT_SERVICE_ID = "srv-dadnjngu01pc73bj9tag"
REQUEST_PATTERN = re.compile(r'"(GET|POST) ([^ ?"]+)(?:\?[^ "]*)? HTTP/[^"]+" (\d{3})')
EVENT_PATTERN = re.compile(r'"event"\s*:\s*"([a-z_]+)"')


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
        event = EVENT_PATTERN.search(message)
        if event:
            counts[event.group(1)] += 1

        request = REQUEST_PATTERN.search(message)
        if not request:
            continue
        method, path, status = request.groups()
        if status.startswith(("2", "3")):
            if method == "GET" and path == "/":
                counts["page_views"] += 1
            elif method == "POST" and path == "/fortune":
                counts["fortune_requests"] += 1
            elif method == "GET" and path == "/premium":
                counts["premium_views"] += 1
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderログから初期反応を集計します")
    parser.add_argument("--hours", type=int, default=24, help="何時間前まで集計するか（既定: 24）")
    parser.add_argument("--service", default=DEFAULT_SERVICE_ID, help="Render service ID")
    args = parser.parse_args()

    start = datetime.now(timezone.utc) - timedelta(hours=max(1, args.hours))
    command = [
        "render", "logs", "--resources", args.service,
        "--start", start.isoformat().replace("+00:00", "Z"),
        "--limit", "1000", "--output", "json",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    counts = summarize(parse_json_stream(result.stdout))
    if not counts.get("fortune_completed"):
        counts["fortune_completed"] = counts.get("fortune_requests", 0)

    labels = (
        ("page_views", "トップ表示"),
        ("fortune_started", "鑑定開始"),
        ("fortune_completed", "鑑定完了"),
        ("share_started", "共有操作"),
        ("share_completed", "共有完了"),
        ("premium_clicked", "極み版クリック"),
        ("premium_views", "極み版表示"),
    )
    print(f"直近 {args.hours} 時間")
    for key, label in labels:
        print(f"{label:<12} {counts.get(key, 0):>6}")

    views = counts.get("page_views", 0)
    completed = counts.get("fortune_completed", 0)
    shared = counts.get("share_completed", 0)
    if views:
        print(f"鑑定完了率      {completed / views:>6.1%}")
        print(f"共有完了率      {shared / views:>6.1%}")


if __name__ == "__main__":
    main()
