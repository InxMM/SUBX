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


def download_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "proxy-to-resin/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()

    return json.loads(raw.decode("utf-8"))


def extract_proxy(item):
    if isinstance(item, str):
        proxy = item.strip()
        return proxy if proxy.startswith(ALLOWED_SCHEMES) else None

    if not isinstance(item, dict):
        return None

    proxy = item.get("proxy")
    if isinstance(proxy, str):
        proxy = proxy.strip()
        if proxy.startswith(ALLOWED_SCHEMES):
            return proxy

    # Fallback for slightly different JSON layouts.
    protocol = (
        item.get("protocol")
        or item.get("type")
        or item.get("scheme")
    )
    host = (
        item.get("ip")
        or item.get("host")
        or item.get("address")
    )
    port = item.get("port")

    if not protocol or not host or not port:
        return None

    protocol = str(protocol).lower().strip()
    if protocol == "socks":
        protocol = "socks5"

    if f"{protocol}://" not in ALLOWED_SCHEMES:
        return None

    username = item.get("username") or item.get("user")
    password = item.get("password") or item.get("pass")

    auth = ""
    if username is not None:
        auth = str(username)
        if password is not None:
            auth += ":" + str(password)
        auth += "@"

    return f"{protocol}://{auth}{host}:{port}"


def main():
    proxies = []
    seen = set()
    success_sources = 0

    for url in SOURCES:
        print(f"[FETCH] {url}")

        try:
            data = download_json(url)
        except Exception as exc:
            print(f"[WARN] Failed to fetch {url}: {exc}", file=sys.stderr)
            continue

        if isinstance(data, dict):
            # Support common wrappers such as {"data": [...]} or {"proxies": [...]}
            for key in ("data", "proxies", "items", "results"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break

        if not isinstance(data, list):
            print(f"[WARN] Unsupported JSON structure from {url}", file=sys.stderr)
            continue

        added = 0

        for item in data:
            proxy = extract_proxy(item)
            if not proxy or proxy in seen:
                continue

            seen.add(proxy)
            proxies.append(proxy)
            added += 1

        success_sources += 1
        print(f"[OK] Added {added} unique proxies")

    if success_sources == 0:
        print("[ERROR] All sources failed. Existing subscription will not be overwritten.", file=sys.stderr)
        sys.exit(1)

    # Stable ordering makes Git diffs smaller and subscription output reproducible.
    proxies.sort()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(proxies) + ("\n" if proxies else ""),
        encoding="utf-8",
    )

    print(f"[DONE] Total unique proxies: {len(proxies)}")
    print(f"[DONE] Output: {OUTPUT}")


if __name__ == "__main__":
    main()
