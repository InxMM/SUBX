#!/usr/bin/env python3
import json
import sys
import urllib.request
from pathlib import Path

SOURCES = [
    "https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/http.json",
    "https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/https.json",
    "https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/socks5.json",
]

OUTPUT = Path("dist/resin.txt")

ALLOWED_SCHEMES = (
    "http://",
    "https://",
    "socks5://",
    "socks5h://",
)


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SUBX-Resin-Converter/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_proxy(item):
    # Current EDT format: {"proxy": "http://IP:PORT", ...}
    if isinstance(item, dict):
        proxy = item.get("proxy")
        if isinstance(proxy, str):
            proxy = proxy.strip()
            if proxy.startswith(ALLOWED_SCHEMES):
                return proxy

    # Also tolerate a plain string list.
    if isinstance(item, str):
        proxy = item.strip()
        if proxy.startswith(ALLOWED_SCHEMES):
            return proxy

    return None


def main():
    proxies = set()
    successful_sources = 0

    for url in SOURCES:
        print(f"[FETCH] {url}")

        try:
            data = fetch_json(url)
        except Exception as exc:
            print(f"[WARN] Failed: {exc}", file=sys.stderr)
            continue

        # Tolerate common wrappers if upstream changes slightly.
        if isinstance(data, dict):
            for key in ("data", "proxies", "items", "results"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break

        if not isinstance(data, list):
            print(f"[WARN] Unsupported JSON structure: {url}", file=sys.stderr)
            continue

        before = len(proxies)

        for item in data:
            proxy = extract_proxy(item)
            if proxy:
                proxies.add(proxy)

        added = len(proxies) - before
        successful_sources += 1
        print(f"[OK] Added {added} unique proxies")

    # Do not overwrite the previous subscription if every upstream source fails.
    if successful_sources == 0:
        print(
            "[ERROR] All sources failed. Existing dist/resin.txt is kept.",
            file=sys.stderr,
        )
        sys.exit(1)

    output = sorted(proxies)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(output) + ("\n" if output else ""),
        encoding="utf-8",
    )

    print(f"[DONE] Total unique proxies: {len(output)}")
    print(f"[DONE] Written to: {OUTPUT}")


if __name__ == "__main__":
    main()
