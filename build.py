#!/usr/bin/env python3
import ipaddress
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

SOURCES = [
    "https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/http.json",
    "https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/https.json",
    "https://raw.githubusercontent.com/EDT-Pages/Proxy-List/refs/heads/main/data/socks5.json",
]

OUTPUT = Path("dist/resin.txt")
STATS_OUTPUT = Path("dist/stats.json")

ALLOWED_SCHEMES = ("http://", "https://", "socks5://", "socks5h://")

TEST_URL = os.getenv(
    "PROXY_TEST_URL",
    "https://api64.ipify.org?format=json",
).strip()

CONCURRENCY = max(
    1,
    min(256, int(os.getenv("PROXY_TEST_CONCURRENCY", "64")))
)

TIMEOUT = max(
    1.0,
    min(60.0, float(os.getenv("PROXY_TEST_TIMEOUT", "8")))
)

RETRIES = max(
    0,
    min(3, int(os.getenv("PROXY_TEST_RETRIES", "1")))
)


def download_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "proxy-to-resin/2.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


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

    protocol = item.get("protocol") or item.get("type") or item.get("scheme")
    host = item.get("ip") or item.get("host") or item.get("address")
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


def protocol_of(proxy: str) -> str:
    return proxy.split("://", 1)[0].lower()


def alternative_test_urls(proxy: str):
    """
    Test the URI as supplied.

    Some public "HTTPS proxy" lists use https:// to mean that the proxy can
    tunnel HTTPS traffic, while the connection to the proxy itself is still
    plain HTTP. In that case also try the same endpoint as http://.

    The original URI is always preserved in resin.txt.
    """
    yield proxy

    if proxy.startswith("https://"):
        yield "http://" + proxy[len("https://"):]


def valid_ip_response(response: requests.Response):
    if response.status_code != 200:
        return None

    body = response.text.strip()
    candidate = None

    try:
        data = response.json()
        if isinstance(data, dict):
            candidate = data.get("ip")
    except Exception:
        candidate = body

    if not candidate:
        candidate = body

    candidate = str(candidate).strip()

    try:
        ipaddress.ip_address(candidate)
        return candidate
    except ValueError:
        return None


def test_proxy(proxy: str):
    last_error = None
    started = time.monotonic()

    for test_proxy in alternative_test_urls(proxy):
        for attempt in range(RETRIES + 1):
            session = requests.Session()
            session.trust_env = False

            try:
                response = session.get(
                    TEST_URL,
                    proxies={
                        "http": test_proxy,
                        "https": test_proxy,
                    },
                    timeout=(min(4.0, TIMEOUT), TIMEOUT),
                    allow_redirects=False,
                    headers={
                        "User-Agent": "proxy-to-resin-check/2.0",
                        "Accept": "application/json,text/plain;q=0.9,*/*;q=0.1",
                        "Connection": "close",
                    },
                )

                exit_ip = valid_ip_response(response)
                response.close()

                if exit_ip:
                    latency_ms = int((time.monotonic() - started) * 1000)
                    return {
                        "proxy": proxy,
                        "alive": True,
                        "exit_ip": exit_ip,
                        "latency_ms": latency_ms,
                        "tested_via": test_proxy,
                        "error": None,
                    }

                last_error = f"HTTP {response.status_code} / invalid IP response"

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"

            finally:
                session.close()

            if attempt < RETRIES:
                time.sleep(0.15)

    return {
        "proxy": proxy,
        "alive": False,
        "exit_ip": None,
        "latency_ms": None,
        "tested_via": None,
        "error": last_error,
    }


def fetch_all():
    proxies = []
    seen = set()
    source_stats = []

    for url in SOURCES:
        print(f"[FETCH] {url}")

        try:
            data = download_json(url)
        except Exception as exc:
            print(f"[WARN] Failed to fetch {url}: {exc}", file=sys.stderr)
            source_stats.append({
                "url": url,
                "ok": False,
                "added": 0,
                "error": str(exc),
            })
            continue

        if isinstance(data, dict):
            for key in ("data", "proxies", "items", "results"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break

        if not isinstance(data, list):
            print(f"[WARN] Unsupported JSON structure from {url}", file=sys.stderr)
            source_stats.append({
                "url": url,
                "ok": False,
                "added": 0,
                "error": "unsupported JSON structure",
            })
            continue

        added = 0
        for item in data:
            proxy = extract_proxy(item)
            if not proxy or proxy in seen:
                continue
            seen.add(proxy)
            proxies.append(proxy)
            added += 1

        source_stats.append({
            "url": url,
            "ok": True,
            "added": added,
            "error": None,
        })
        print(f"[OK] Added {added} unique proxies")

    return proxies, source_stats


def main():
    proxies, source_stats = fetch_all()

    if not proxies:
        print(
            "[ERROR] No proxies were fetched. Existing subscription will not be overwritten.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[TEST] Testing {len(proxies)} proxies "
        f"(concurrency={CONCURRENCY}, timeout={TIMEOUT}s, retries={RETRIES})"
    )
    print(f"[TEST] Target: {TEST_URL}")

    alive = []
    failures = 0
    completed = 0
    total = len(proxies)

    protocol_totals = {}
    protocol_alive = {}

    for proxy in proxies:
        proto = protocol_of(proxy)
        protocol_totals[proto] = protocol_totals.get(proto, 0) + 1

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(test_proxy, proxy): proxy for proxy in proxies}

        for future in as_completed(futures):
            proxy = futures[future]
            completed += 1

            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "proxy": proxy,
                    "alive": False,
                    "exit_ip": None,
                    "latency_ms": None,
                    "tested_via": None,
                    "error": f"worker error: {exc}",
                }

            if result["alive"]:
                alive.append(result)
                proto = protocol_of(proxy)
                protocol_alive[proto] = protocol_alive.get(proto, 0) + 1
                print(
                    f"[LIVE] {proxy} -> {result['exit_ip']} "
                    f"({result['latency_ms']} ms)"
                )
            else:
                failures += 1

            if completed % 100 == 0 or completed == total:
                print(
                    f"[PROGRESS] {completed}/{total} checked, "
                    f"{len(alive)} alive, {failures} failed"
                )

    # Safety: if the checker unexpectedly returns zero live nodes, do not destroy
    # the last known-good subscription.
    if not alive:
        print(
            "[ERROR] Zero live proxies found. Existing resin.txt will not be overwritten.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Fastest proxies first; tie-break by URI for stable output.
    alive.sort(key=lambda x: (x["latency_ms"], x["proxy"]))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "\n".join(item["proxy"] for item in alive) + "\n",
        encoding="utf-8",
    )

    stats = {
        "test_url": TEST_URL,
        "total_fetched_unique": len(proxies),
        "total_alive": len(alive),
        "total_failed": failures,
        "concurrency": CONCURRENCY,
        "timeout_seconds": TIMEOUT,
        "retries": RETRIES,
        "protocol_totals": protocol_totals,
        "protocol_alive": protocol_alive,
        "sources": source_stats,
        "alive": alive,
    }

    STATS_OUTPUT.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[DONE] Alive: {len(alive)}/{len(proxies)}")
    print(f"[DONE] Subscription: {OUTPUT}")
    print(f"[DONE] Stats: {STATS_OUTPUT}")


if __name__ == "__main__":
    main()
