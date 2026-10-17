#!/usr/bin/env python3
"""Print the wayfinder frontier from local ticket frontmatter."""

from pathlib import Path

import re
import sys

ROOT = Path(__file__).resolve().parent
TICKETS = ROOT / "tickets"


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [
                item.strip().strip("\"'")
                for item in value[1:-1].split(",")
                if item.strip()
            ]
            data[key] = items
        elif value in ("", "null", "~"):
            data[key] = None
        else:
            data[key] = value.strip("\"'")
    return data


def load_tickets():
    tickets = []
    for path in sorted(TICKETS.glob("*.md")):
        meta = parse_frontmatter(path)
        if meta:
            meta["_path"] = path
            tickets.append(meta)
    return tickets


def main():
    tickets = load_tickets()
    closed = {t.get("id") for t in tickets if t.get("status") == "closed"}

    def unblocked(ticket):
        return all(dep in closed for dep in (ticket.get("blocked_by") or []))

    if "--all" in sys.argv:
        for ticket in tickets:
            print(
                f"{ticket.get('id', '?'):>4}  "
                f"{ticket.get('status', '?'):<6}  "
                f"{ticket.get('type', '?'):<9}  "
                f"{ticket.get('mode', '?'):<4}  "
                f"{ticket.get('claimed_by') or '-':<20}  "
                f"{ticket.get('title', '?')}"
            )
        return

    if "--research" in sys.argv:
        tickets = [t for t in tickets if t.get("type") == "research"]

    frontier = [
        t
        for t in tickets
        if t.get("status") == "open" and not t.get("claimed_by") and unblocked(t)
    ]
    if not frontier:
        print("Frontier is empty.")
        return
    for ticket in frontier:
        print(
            f"[{ticket.get('id', '?')}] {ticket.get('title', '?')} "
            f"({ticket.get('type', '?')}/{ticket.get('mode', '?')}) "
            f"- {ticket['_path'].name}"
        )


if __name__ == "__main__":
    main()
