#!/usr/bin/env python3
"""
Exploration script: dump raw HTML sections and parsed data from AudiobookBay.

Usage:
    python explore_fields.py [query] [--detail]

    query   - search term (default: "tolkien")
    --detail - also fetch the first result's detail page and dump its raw HTML

Examples:
    python explore_fields.py
    python explore_fields.py "stephen king" --detail
"""

import sys
import os
import json
import pprint
import re

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

import requests
from bs4 import BeautifulSoup
from scraper.audiobookbay_scraper import (
    _abb_request,
    _build_request_headers,
    _with_mirror_retry,
    _extract_posts_from_page,
    get_active_hostname,
    REQUEST_TIMEOUT,
    MIRROR_HOSTNAMES,
)

QUERY = "tolkien"
FETCH_DETAIL = False

for arg in sys.argv[1:]:
    if arg == "--detail":
        FETCH_DETAIL = True
    elif not arg.startswith("-"):
        QUERY = arg


def fetch_search_page(query: str, page: int = 1):
    def _do(host):
        url = f"https://{host}/page/{page}/?s={query.replace(' ', '+')}&cat=undefined%2Cundefined"
        resp = _abb_request("GET", url, headers=_build_request_headers(), timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            raise requests.exceptions.RequestException(f"HTTP {resp.status_code}")
        return resp.text
    return _with_mirror_retry(_do)


def dump_post_sections(raw_html: str, max_posts: int = 3):
    """Print the raw HTML of each major section inside the first few posts."""
    soup = BeautifulSoup(raw_html, "html.parser")
    posts = soup.select("div.post")
    print(f"\n{'='*60}")
    print(f"Found {len(posts)} post divs on page. Showing first {min(max_posts, len(posts))}.")
    print(f"{'='*60}")

    for i, post in enumerate(posts[:max_posts]):
        print(f"\n{'─'*60}")
        print(f"POST #{i+1}  classes={post.get('class', [])}")
        print(f"{'─'*60}")

        # Show every top-level child element with its class/id/tag
        for child in post.children:
            if hasattr(child, "name") and child.name:
                cls = child.get("class", [])
                eid = child.get("id", "")
                label = f"<{child.name} class={cls} id={eid!r}>"
                inner_text = child.get_text(" ", strip=True)[:120]
                print(f"\n  {label}")
                print(f"  TEXT PREVIEW: {inner_text!r}")

                # One level deeper
                for sub in child.children:
                    if hasattr(sub, "name") and sub.name:
                        scls = sub.get("class", [])
                        sid = sub.get("id", "")
                        slabel = f"<{sub.name} class={scls} id={sid!r}>"
                        stext = sub.get_text(" ", strip=True)[:100]
                        print(f"      {slabel}  →  {stext!r}")


def dump_structured_parsed(raw_html: str, max_posts: int = 3):
    """Pretty-print the fully parsed post dicts."""
    soup = BeautifulSoup(raw_html, "html.parser")
    results = _extract_posts_from_page(soup)
    print(f"\n{'='*60}")
    print(f"PARSED RESULTS ({len(results)} total, showing first {min(max_posts, len(results))})")
    print(f"{'='*60}")
    for i, r in enumerate(results[:max_posts]):
        print(f"\n--- Result #{i+1} ---")
        pprint.pprint(r, width=80)


def fetch_and_dump_detail(detail_url: str):
    """Fetch a detail page and print every table row / section found."""
    print(f"\n{'='*60}")
    print(f"DETAIL PAGE: {detail_url}")
    print(f"{'='*60}")

    resp = _abb_request("GET", detail_url, headers=_build_request_headers(), timeout=REQUEST_TIMEOUT)
    if resp.status_code != 200:
        print(f"  Failed: HTTP {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Table rows (torrent info) ---
    print("\n[TABLE ROWS]")
    for row in soup.select("table tr"):
        cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
        if cells:
            print(" | ".join(cells))

    # --- All headings ---
    print("\n[HEADINGS]")
    for tag in ["h1", "h2", "h3", "h4"]:
        for el in soup.find_all(tag):
            print(f"  <{tag}>: {el.get_text(strip=True)!r}")

    # --- Any <div> or <p> with class names (top-level interesting blocks) ---
    print("\n[NAMED SECTIONS]")
    for el in soup.find_all(["div", "section", "article"], class_=True):
        cls = " ".join(el.get("class", []))
        text = el.get_text(" ", strip=True)[:150]
        print(f"  .{cls}  →  {text!r}")

    # --- Links (anchors) ---
    print("\n[ALL LINKS]")
    for a in soup.find_all("a", href=True):
        print(f"  [{a.get_text(strip=True)!r}]  {a['href']}")

    # --- Raw text of the whole page (for grep-friendly reading) ---
    page_text = soup.get_text("\n", strip=True)
    out_path = "/tmp/abb_detail_page.txt"
    with open(out_path, "w") as f:
        f.write(page_text)
    print(f"\n  Full page text saved to: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

print(f"\nQuerying AudiobookBay for: {QUERY!r}")
print(f"Active mirror: {get_active_hostname()}")

raw_html = fetch_search_page(QUERY, page=1)

# Save raw search HTML for manual inspection
search_html_path = "/tmp/abb_search_page.html"
with open(search_html_path, "w") as f:
    f.write(raw_html)
print(f"Raw search HTML saved to: {search_html_path}")

dump_post_sections(raw_html, max_posts=2)
dump_structured_parsed(raw_html, max_posts=3)

if FETCH_DETAIL:
    soup = BeautifulSoup(raw_html, "html.parser")
    results = _extract_posts_from_page(soup)
    if results:
        first_url = results[0].get("link") or results[0].get("post_url")
        if first_url:
            fetch_and_dump_detail(first_url)
        else:
            print("\nNo detail URL found in first result.")
    else:
        print("\nNo results parsed to follow for detail page.")
else:
    print("\nTip: run with --detail to also dump the first result's detail page.")
