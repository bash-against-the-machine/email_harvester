#!/usr/bin/env python3
"""
email_harvester.py - Search for email addresses associated with a domain.

Requires: pip install ddgs requests beautifulsoup4

Usage:
    python3 email_harvester.py example.com
    python3 email_harvester.py example.com --results 20
    python3 email_harvester.py example.com /path/to/output/dir
    python3 email_harvester.py domains.txt
    python3 email_harvester.py domains.txt /path/to/output/dir
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE
)

COMMON_PATHS = [
    "/contact", "/contact-us", "/about", "/about-us",
    "/support", "/help", "/info", "/team", "/staff",
    "/press", "/media", "/legal", "/privacy", "/careers",
]


def build_queries(domain: str) -> list[str]:
    return [
        f'"@{domain}"',
        f'site:{domain} email',
        f'"{domain}" email contact',
        f'intext:"@{domain}"',
    ]


def extract_emails(text: str, domain: str) -> set[str]:
    """Return all emails in text that belong to the target domain."""
    return {e.lower() for e in EMAIL_RE.findall(text) if e.lower().endswith(f"@{domain}")}


def ddg_search(query: str, max_results: int) -> list[dict]:
    """Return DDG search results as a list of dicts."""
    try:
        return list(DDGS().text(query, max_results=max_results))
    except Exception as e:
        print(f"  [!] DDG search failed: {e}", file=sys.stderr)
        return []


def scrape_page(url: str, domain: str) -> set[str]:
    """Fetch a URL and extract emails matching the domain."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return extract_emails(resp.text, domain)
    except requests.RequestException:
        return set()


def scrape_common_pages(domain: str) -> set[str]:
    """Directly scrape common contact/about paths on the domain."""
    print(f"[*] Scraping common pages on {domain}", file=sys.stderr)
    all_emails: set[str] = set()
    for path in COMMON_PATHS:
        for scheme in ("https", "http"):
            url = f"{scheme}://{domain}{path}"
            found = scrape_page(url, domain)
            if found:
                print(f"  [+] Found on {url}: {found}", file=sys.stderr)
                all_emails.update(found)
                break  # no need to try http if https worked
    return all_emails


def harvest(domain: str, num_results: int = 10) -> set[str]:
    all_emails: set[str] = set()
    seen_urls: set[str] = set()

    # Phase 1: direct scrape of common pages (no search needed)
    all_emails.update(scrape_common_pages(domain))

    # Phase 2: DDG search + scrape result pages
    for query in build_queries(domain):
        print(f"[*] Querying: {query}", file=sys.stderr)
        results = ddg_search(query, max_results=num_results)
        print(f"  [i] {len(results)} results returned", file=sys.stderr)

        for r in results:
            # Mine the snippet/title directly
            snippet_text = f"{r.get('title', '')} {r.get('body', '')}"
            found = extract_emails(snippet_text, domain)
            if found:
                print(f"  [+] Found in snippet: {found}", file=sys.stderr)
            all_emails.update(found)

            # Scrape the result page
            url = r.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                page_found = scrape_page(url, domain)
                if page_found:
                    print(f"  [+] Found on {url}: {page_found}", file=sys.stderr)
                all_emails.update(page_found)

        time.sleep(1.5)

    return all_emails


def resolve_target(target: str) -> list[str]:
    """Return a list of domains from the target argument.

    If target is an existing file, read one domain per line.
    If target looks like a file path but doesn't exist, exit with an error.
    Otherwise treat target as a single domain name.
    """
    if os.path.isfile(target):
        with open(target) as f:
            domains = [line.strip() for line in f if line.strip()]
        if not domains:
            print(f"[!] File '{target}' is empty or contains no valid domains.", file=sys.stderr)
            sys.exit(1)
        return domains

    # Looks like an intended file path (contains a separator or file extension)
    looks_like_path = os.sep in target or "/" in target or target.endswith(".txt")
    if looks_like_path:
        print(f"[!] File not found: {target}", file=sys.stderr)
        sys.exit(1)

    return [target]


def normalize_domain(domain: str) -> str:
    domain = domain.strip().lstrip("@").lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def save_results(emails: set[str], domain: str, output_dir: str) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{domain}_{timestamp}.txt")
    with open(output_file, "w") as f:
        f.write("\n".join(sorted(emails)) + "\n")
    print(f"\n[+] Results saved to: {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Harvest email addresses for a domain using DuckDuckGo + direct scraping."
    )
    parser.add_argument(
        "target",
        help="Target domain (e.g. example.com) or path to a text file with one domain per line",
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help="Directory to save output files (created if needed; defaults to script directory)",
    )
    parser.add_argument(
        "-n", "--results",
        type=int,
        default=10,
        metavar="N",
        help="Number of search results to fetch per query (default: 10)",
    )
    args = parser.parse_args()

    # Resolve output directory
    if args.output_dir:
        output_dir = args.output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"[*] Created output directory: {output_dir}", file=sys.stderr)
    else:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    # Resolve domain list
    domains = resolve_target(args.target)

    for raw_domain in domains:
        domain = normalize_domain(raw_domain)
        if not domain:
            continue

        print(f"\n[*] Harvesting emails for: {domain}\n", file=sys.stderr)

        emails = harvest(domain, num_results=args.results)

        if emails:
            print(f"\n[+] Found {len(emails)} unique email address(es) for {domain}:")
            for email in sorted(emails):
                print(email)
            save_results(emails, domain, output_dir)
        else:
            print(f"\n[-] No email addresses found for {domain}.")


if __name__ == "__main__":
    main()
