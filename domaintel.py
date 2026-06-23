#!/usr/bin/env python3
"""domaintel — domain registration lookup over RDAP.

RDAP is the modern, JSON-based successor to WHOIS. domaintel resolves a
domain through the RDAP bootstrap and reports the registrar, key dates
(registration, expiry, last update), nameservers, and status codes, plus a
computed domain age and days-to-expiry.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

__version__ = "1.0.0"

RDAP_BOOTSTRAP = "https://rdap.org/domain/"


class Colors:
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for n in ("GREEN", "YELLOW", "RED", "CYAN", "DIM", "BOLD", "RESET"):
            setattr(cls, n, "")


def fetch_rdap(domain: str, timeout: float) -> dict:
    req = urllib.request.Request(
        RDAP_BOOTSTRAP + domain,
        headers={"User-Agent": f"domaintel/{__version__}", "Accept": "application/rdap+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def registrar_name(data: dict) -> Optional[str]:
    for entity in data.get("entities", []):
        if "registrar" in entity.get("roles", []):
            vcard = entity.get("vcardArray", [None, []])[1]
            for item in vcard:
                if item and item[0] == "fn":
                    return item[3]
            return entity.get("handle")
    return None


def summarize(data: dict) -> dict:
    events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}
    nameservers = sorted(
        ns.get("ldhName", "").lower() for ns in data.get("nameservers", []) if ns.get("ldhName")
    )
    return {
        "domain": data.get("ldhName", "").lower(),
        "registrar": registrar_name(data),
        "registered": events.get("registration"),
        "expires": events.get("expiration"),
        "updated": events.get("last changed"),
        "status": data.get("status", []),
        "nameservers": nameservers,
    }


def days_between(value: Optional[str]) -> Optional[int]:
    d = parse_date(value) if value else None
    if not d:
        return None
    return (d - datetime.now(timezone.utc)).days


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="domaintel", description=__doc__.splitlines()[0])
    p.add_argument("domain")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    if args.no_color or args.json or not sys.stdout.isatty():
        Colors.disable()
    c = Colors

    domain = args.domain.strip().lower().strip(".")
    try:
        data = fetch_rdap(domain, args.timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"no RDAP record for {domain} (unregistered or unsupported TLD)",
                  file=sys.stderr)
            return 1
        print(f"error: RDAP lookup failed: HTTP {exc.code}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - report any lookup failure cleanly
        print(f"error: {exc}", file=sys.stderr)
        return 2

    info = summarize(data)

    if args.json:
        print(json.dumps(info, indent=2))
        return 0

    age_days = days_between(info["registered"])
    exp_days = days_between(info["expires"])

    print(f"{c.BOLD}domaintel{c.RESET} {c.DIM}{info['domain']}{c.RESET}\n")
    row = lambda k, v: print(f"  {c.CYAN}{k:<12}{c.RESET}{v}")
    row("registrar", info["registrar"] or "-")
    if info["registered"]:
        extra = f"  {c.DIM}({-age_days} days old){c.RESET}" if age_days is not None else ""
        row("registered", f"{info['registered']}{extra}")
    if info["expires"]:
        ec = c.GREEN if (exp_days or 0) > 30 else c.YELLOW if (exp_days or 0) > 0 else c.RED
        extra = f"  {ec}({exp_days} days){c.RESET}" if exp_days is not None else ""
        row("expires", f"{info['expires']}{extra}")
    if info["updated"]:
        row("updated", info["updated"])
    if info["status"]:
        row("status", ", ".join(info["status"]))
    if info["nameservers"]:
        print(f"  {c.CYAN}nameservers{c.RESET}")
        for ns in info["nameservers"]:
            print(f"    {ns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
