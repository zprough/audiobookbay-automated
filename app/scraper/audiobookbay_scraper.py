"""
AudiobookBay Scraper Module
Handles all AudiobookBay scraping, magnet link extraction, and data processing.
"""

import os
import re
import requests
import base64
import html as htmllib
from typing import List, Dict, Optional, Any, Tuple, Callable
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
from datetime import datetime
from functools import lru_cache
import random
import time

# =============================================================================
# CONFIGURATION
# =============================================================================

# AudiobookBay Configuration (from environment)
# Primary hostname (can be overridden). Mirrors will be tried in order until one responds.
_ENV_HOST = os.getenv("ABB_HOSTNAME", "audiobookbay.lu").strip()
PAGE_LIMIT: int = int(os.getenv("PAGE_LIMIT", 5))

# Ordered list of mirrors. If user supplied a custom host, keep it first.
MIRROR_HOSTNAMES: List[str] = []
_default_mirrors = [
    "audiobookbay.lu",
    "audiobookbay.fi",
    "audiobookbay.is",
    "theaudiobookbay.se",
]

if _ENV_HOST and _ENV_HOST not in _default_mirrors:
    MIRROR_HOSTNAMES.append(_ENV_HOST)
for m in _default_mirrors:
    if m not in MIRROR_HOSTNAMES:
        MIRROR_HOSTNAMES.append(m)

# Per-request timeout (seconds) when probing mirrors / fetching pages
REQUEST_TIMEOUT: float = float(os.getenv("ABB_TIMEOUT", "8"))

# How long (seconds) a HEAD/GET mirror probe may take before moving on (same as REQUEST_TIMEOUT for now)
PROBE_TIMEOUT: float = REQUEST_TIMEOUT

# Cache the selected working mirror for the life of the process. If it fails mid-run, we will clear cache.
_ACTIVE_MIRROR: Optional[str] = None

def _probe_mirror(hostname: str) -> bool:
    """Check if a mirror is reachable quickly.

    Uses a lightweight GET to front page (HEAD sometimes blocked). Returns True on HTTP 200.
    Failures (timeout, connection, non-200) return False.
    """
    url = f"https://{hostname}/"
    try:
        resp = requests.get(url, headers=_build_request_headers(), timeout=PROBE_TIMEOUT)
        if resp.status_code == 200 and resp.text:
            return True
    except requests.exceptions.RequestException:
        return False
    return False

def _select_active_mirror(force_refresh: bool = False) -> str:
    """Return an active mirror, probing in order if needed.

    If force_refresh is True we ignore the cached value and probe again.
    Raises RuntimeError if no mirrors are reachable.
    """
    global _ACTIVE_MIRROR
    if _ACTIVE_MIRROR and not force_refresh:
        return _ACTIVE_MIRROR
    for host in MIRROR_HOSTNAMES:
        if _probe_mirror(host):
            _ACTIVE_MIRROR = host
            if host != MIRROR_HOSTNAMES[0]:
                print(f"[SCRAPER] Switched active AudiobookBay mirror to: {host}")
            return host
    raise RuntimeError("No AudiobookBay mirrors are reachable.")

def get_active_hostname() -> str:
    """Public accessor for currently selected mirror hostname (probing if necessary)."""
    try:
        return _select_active_mirror()
    except Exception as e:
        # Return first configured hostname as fallback (even if unreachable) to avoid crashes where string expected
        print(f"[SCRAPER] Mirror selection failed: {e}")
        return MIRROR_HOSTNAMES[0]

# Request header / incognito configuration
INCOGNITO_MODE: bool = os.getenv("INCOGNITO_MODE", "false").lower() in {"1", "true", "yes", "on"}
ROTATE_USER_AGENT: bool = os.getenv("ROTATE_USER_AGENT", "true").lower() in {"1", "true", "yes", "on"}
DISABLE_CACHE_BUST: bool = os.getenv("DISABLE_CACHE_BUST", "false").lower() in {"1", "true", "yes", "on"}

BASE_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
]

def _pick_user_agent() -> str:
    return random.choice(BASE_USER_AGENTS) if ROTATE_USER_AGENT else BASE_USER_AGENTS[0]

def _build_request_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {
        'User-Agent': _pick_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'close' if INCOGNITO_MODE else 'keep-alive',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    if extra:
        headers.update(extra)
    return headers

# Preserve symbol for compatibility (represents one generated header set at import time)
DEFAULT_HEADERS = _build_request_headers()

# Default trackers for magnet links when none are found
DEFAULT_TRACKERS = [
    "udp://tracker.openbittorrent.com:80",
    "udp://opentor.org:2710", 
    "udp://tracker.ccc.de:80",
    "udp://tracker.blackunicorn.xyz:6969",
    "udp://tracker.coppersurfer.tk:6969",
    "udp://tracker.leechers-paradise.org:6969"
]

# =============================================================================
# SCRAPING FUNCTIONS
# =============================================================================

def search_audiobookbay(query: str, max_pages: Optional[int] = None) -> List[Dict[str, str]]:
    """
    Search AudiobookBay for audiobooks matching the given query.
    
    Args:
        query (str): Search query string
        max_pages (int, optional): Maximum number of pages to search. 
                                 Defaults to PAGE_LIMIT from environment.
    
    Returns:
        List[Dict[str, str]]: List of dictionaries containing title, link, and cover
    """
    if max_pages is None:
        max_pages = PAGE_LIMIT
        
    results = []
    
    for page in range(1, max_pages + 1):
        try:
            page_results = _scrape_search_page(query, page)
            if not page_results:
                # No results on this page, likely reached the end
                break
            results.extend(page_results)
            
        except Exception as e:
            print(f"[SCRAPER] Error on page {page}: {e}")
            break
    
    print(f"[SCRAPER] Found {len(results)} results for query: '{query}'")
    return results

def _with_mirror_retry(fn: Callable[[str], Any]) -> Any:
    """Execute a function that depends on a base hostname, retrying across mirrors on network errors.

    The callable receives the active hostname and should perform work. If it raises a RequestException
    or returns a special value signalling retry (None with attribute _retry), we cycle mirrors.
    """
    last_error: Optional[Exception] = None
    tried: List[str] = []
    for host in MIRROR_HOSTNAMES:
        try:
            # Optimistically set active mirror; if probe fails we'll move on.
            _set_active_mirror(host)
            if not _probe_mirror(host):
                tried.append(host)
                continue
            result = fn(host)
            return result
        except requests.exceptions.RequestException as e:
            last_error = e
            tried.append(host)
            _clear_active_mirror()
            continue
        except Exception as e:  # non-network errors: break early
            last_error = e
            break
    if last_error:
        raise last_error
    raise RuntimeError(f"All mirrors failed ({', '.join(tried)})")

def _set_active_mirror(host: str) -> None:
    global _ACTIVE_MIRROR
    _ACTIVE_MIRROR = host

def _clear_active_mirror() -> None:
    global _ACTIVE_MIRROR
    _ACTIVE_MIRROR = None

def _scrape_search_page(query: str, page: int) -> List[Dict[str, str]]:
    """
    Scrape a single search results page from AudiobookBay.
    
    Args:
        query (str): Search query string
        page (int): Page number to scrape
        
    Returns:
        List[Dict[str, str]]: List of results from this page
    """
    def _do(host: str) -> List[Dict[str, str]]:
        base_url = f"https://{host}/page/{page}/?s={query.replace(' ', '+')}&cat=undefined%2Cundefined"
        if INCOGNITO_MODE and not DISABLE_CACHE_BUST:
            sep = '&' if '?' in base_url else '?'
            url = f"{base_url}{sep}_cb={int(time.time()*1000)}{random.randint(0,999)}"
        else:
            url = base_url
        response = requests.get(url, headers=_build_request_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            raise requests.exceptions.RequestException(f"Status {response.status_code} on {host}")
        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_posts_from_page(soup)
    try:
        return _with_mirror_retry(_do)
    except Exception as e:
        print(f"[SCRAPER] Failed to fetch search page {page} across mirrors: {e}")
        return []

def _extract_posts_from_page(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract post information from a BeautifulSoup parsed page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML page
        
    Returns:
        List[Dict[str, str]]: List of extracted posts with comprehensive information
    """
    results = []
    
    # Find all divs with class "post"
    post_divs = soup.select('div.post')
    
    decoded_posts = []
    
    # First pass: decode base64 encoded posts if needed
    for i, div in enumerate(post_divs):
        try:
            # If post has class re-ab then decode it
            if 're-ab' in div.get('class', []):
                base64_encoded_text = div.text.strip()
                decoded_bytes = base64.b64decode(base64_encoded_text)
                decoded_html = decoded_bytes.decode('utf-8', errors='replace')
                decoded_posts.append(decoded_html)
            else:
                # Use the original HTML content
                decoded_posts.append(str(div))
        except Exception as e:
            print(f"[SCRAPER] Decoding failed for post {i}: {e}")
            # Fallback to original content
            decoded_posts.append(str(div))
    
    # Second pass: parse the decoded content
    for i, post_html in enumerate(decoded_posts):
        try:
            # Parse the comprehensive post information
            post_data = _parse_post_details(post_html)
            
            # Only add posts with valid titles and links
            if post_data.get('title') and post_data.get('link'):
                results.append(post_data)
            
        except Exception as e:
            print(f"[SCRAPER] Error extracting post {i}: {e}")
            continue
    
    return results

def _split_inline_list(text: str) -> List[str]:
    """
    Split inline list text from AudiobookBay.
    
    Args:
        text (str): Raw text to split
        
    Returns:
        List[str]: List of cleaned items
    """
    raw = [t.strip() for t in re.split(r'\xa0|\s{2,}', text) if t.strip()]
    return [re.sub(r'[,\u200b]+$', '', x) for x in raw]

def _parse_posted_block(block_text: str) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
    """
    Parse the posted information block.
    
    Args:
        block_text (str): Text containing posted info
        
    Returns:
        tuple: (posted_date, format, bitrate_kbps, file_size_bytes)
    """
    t = re.sub(r'\s+', ' ', block_text).strip()

    # Extract posted date
    m_date = re.search(r'Posted:\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})', t)
    posted_date = None
    if m_date:
        try:
            posted_date = datetime.strptime(m_date.group(1), "%d %b %Y").date().isoformat()
        except ValueError:
            posted_date = m_date.group(1)

    # Extract format
    m_fmt = re.search(r'Format:\s*([A-Za-z0-9]+)', t)
    fmt = m_fmt.group(1) if m_fmt else None

    # Extract bitrate
    m_br = re.search(r'Bitrate:\s*([0-9?]+)\s*Kbps', t, flags=re.I)
    bitrate_kbps = None if not m_br or m_br.group(1) == '?' else int(m_br.group(1))

    # Extract file size
    m_fs = re.search(r'File Size:\s*([\d.]+)\s*(G|M)Bs?', t, flags=re.I)
    file_size_bytes = None
    if m_fs:
        val = float(m_fs.group(1))
        unit = m_fs.group(2).upper()
        file_size_bytes = int(val * (1024**3 if unit == 'G' else 1024**2))

    return posted_date, fmt, bitrate_kbps, file_size_bytes

def _parse_post_details(html_snippet: str) -> Dict[str, Any]:
    """
    Parse detailed information from a post HTML snippet.
    
    Args:
        html_snippet (str): HTML content of the post
        
    Returns:
        Dict[str, Any]: Comprehensive post information
    """
    if not html_snippet.strip().startswith("<"):
        html_snippet = f"<div>{htmllib.escape(html_snippet)}</div>"

    soup = BeautifulSoup(html_snippet, "html.parser")
    base_url = f"https://{get_active_hostname()}"

    # Extract title and post URL
    a_title = soup.select_one(".postTitle h2 a") or soup.find("a", rel="bookmark")
    title = a_title.get_text(strip=True) if a_title else None
    
    # Handle href extraction safely
    post_url = None
    if a_title and a_title.has_attr("href"):
        try:
            href = a_title["href"]
            post_url = urljoin(base_url, href) if href else None
        except:
            pass

    # Extract categories, language, and keywords from postInfo
    info = soup.select_one(".postInfo")
    categories, language, keywords = [], None, []
    if info:
        info_text = info.get_text(" ", strip=True)
        
        # Extract categories
        m_cat = re.search(r'Category:\s*(.*?)\s*Language:', info_text, flags=re.I)
        if m_cat:
            categories = _split_inline_list(m_cat.group(1))
            
        # Extract language
        m_lang = re.search(r'Language:\s*([A-Za-z]+)', info_text, flags=re.I)
        if m_lang:
            language = m_lang.group(1)
            
        # Extract keywords
        kw_span = info.find("span")
        if kw_span:
            keywords = _split_inline_list(
                kw_span.get_text(" ", strip=True).replace("Keywords:", "").strip()
            )

    # Extract uploader
    uploader_a = soup.select_one(".postContent a[href*='member/users']")
    uploader = uploader_a.get_text(strip=True) if uploader_a else None

    # Extract image URL
    img = soup.select_one(".postContent img")
    image_url = None
    if img and img.has_attr("src"):
        try:
            cover_src = img["src"]
            if cover_src.startswith('//'):
                image_url = 'https:' + cover_src
            elif cover_src.startswith('/'):
                image_url = urljoin(base_url, cover_src)
            else:
                image_url = urljoin(base_url, cover_src)
        except:
            image_url = None

    # Extract posted information block
    posted_block = ""
    for p in soup.select(".postContent p"):
        txt = p.get_text(" ", strip=True)
        if "Posted:" in txt and "File Size:" in txt:
            posted_block = txt
            break
    if not posted_block:
        for p in soup.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if "Posted:" in txt and "File Size:" in txt:
                posted_block = txt
                break

    # Parse posted information
    posted_date, fmt, bitrate_kbps, file_size_bytes = _parse_posted_block(posted_block)
    
    # Format file size for display
    file_size_display = None
    if file_size_bytes:
        if file_size_bytes >= 1024**3:  # GB
            file_size_display = f"{file_size_bytes / (1024**3):.1f} GB"
        elif file_size_bytes >= 1024**2:  # MB
            file_size_display = f"{file_size_bytes / (1024**2):.1f} MB"
        else:
            file_size_display = f"{file_size_bytes / 1024:.1f} KB"

    return {
        "title": title,
        "link": post_url,  # Keep 'link' for compatibility
        "post_url": post_url,  # Match your original field name
        "cover": image_url or "/static/images/default_cover.jpg",  # Keep 'cover' for compatibility with fallback
        "image_url": image_url,  # Match your original field name
        "categories": categories or None,  # Match your original logic
        "language": language,
        "keywords": keywords or None,  # Match your original logic
        "uploader": uploader,
        "posted_date": posted_date,
        "format": fmt,
        "bitrate_kbps": bitrate_kbps,
        "file_size_bytes": file_size_bytes,
        "file_size_display": file_size_display,
    }

# =============================================================================
# MAGNET LINK EXTRACTION
# =============================================================================

def extract_magnet_link(details_url: str) -> Optional[str]:
    """
    Extract magnet link from an AudiobookBay details page.
    
    Args:
        details_url (str): URL of the AudiobookBay details page
        
    Returns:
        Optional[str]: Generated magnet link or None if extraction fails
    """
    try:
        # If the details_url contains an outdated mirror, rewrite to active mirror to reduce failures.
        active_host = get_active_hostname()
        try:
            # Replace only the network location part if it matches a known mirror.
            for mirror in MIRROR_HOSTNAMES:
                if f"//{mirror}" in details_url:
                    details_url = details_url.replace(mirror, active_host)
                    break
        except Exception:
            pass
        if INCOGNITO_MODE and not DISABLE_CACHE_BUST:
            sep = '&' if '?' in details_url else '?'
            details_url_cb = f"{details_url}{sep}_cb={int(time.time()*1000)}{random.randint(0,999)}"
        else:
            details_url_cb = details_url
        response = requests.get(details_url_cb, headers=_build_request_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(f"[SCRAPER] Failed to fetch details page. Status Code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract info hash and trackers
        info_hash = _extract_info_hash(soup)
        if not info_hash:
            return None
            
        trackers = _extract_trackers(soup)
        
        # Generate magnet link
        magnet_link = _build_magnet_link(info_hash, trackers, details_url)
        
        print(f"[SCRAPER] Generated magnet link for: {details_url}")
        return magnet_link

    except requests.exceptions.RequestException as e:
        print(f"[SCRAPER] Network error extracting magnet: {e}")
        return None
    except Exception as e:
        print(f"[SCRAPER] Error extracting magnet link: {e}")
        return None

def _extract_info_hash(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract the info hash from the AudiobookBay page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML page
        
    Returns:
        Optional[str]: Info hash or None if not found
    """
    info_hash_row = soup.find('td', string=re.compile(r'Info Hash', re.IGNORECASE))
    if not info_hash_row:
        print("[SCRAPER] Info Hash not found on page")
        return None
        
    hash_cell = info_hash_row.find_next_sibling('td')
    if not hash_cell:
        print("[SCRAPER] Info Hash value cell not found")
        return None
        
    return hash_cell.text.strip()

def _extract_trackers(soup: BeautifulSoup) -> List[str]:
    """
    Extract tracker URLs from the AudiobookBay page.
    
    Args:
        soup (BeautifulSoup): Parsed HTML page
        
    Returns:
        List[str]: List of tracker URLs
    """
    tracker_rows = soup.find_all('td', string=re.compile(r'udp://|http://', re.IGNORECASE))
    trackers = [row.text.strip() for row in tracker_rows if row.text.strip()]

    if not trackers:
        print("[SCRAPER] No trackers found, using defaults")
        return DEFAULT_TRACKERS
        
    return trackers

def _build_magnet_link(info_hash: str, trackers: List[str], source_url: str) -> str:
    """
    Build a magnet link from components.
    
    Args:
        info_hash (str): BitTorrent info hash
        trackers (List[str]): List of tracker URLs
        source_url (str): Source URL for display name
        
    Returns:
        str: Complete magnet link
    """
    # Create display name from URL
    display_name = source_url.split('/')[-2] if source_url.endswith('/') else source_url.split('/')[-1]
    display_name = display_name.replace('-', ' ').title()
    
    # Build tracker parameters
    trackers_query = "&".join(f"tr={quote(tracker)}" for tracker in trackers)
    
    # Construct magnet link
    magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={quote(display_name)}&{trackers_query}"
    
    return magnet_link

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def sanitize_title(title: str) -> str:
    """
    Sanitize a title by removing invalid filesystem characters.
    
    Args:
        title (str): The title to sanitize
        
    Returns:
        str: Sanitized title safe for use as a directory name
    """
    if not title:
        return "Unknown"
        
    # Remove invalid filesystem characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    
    # Remove extra whitespace and limit length
    sanitized = ' '.join(sanitized.split())
    
    # Limit length to prevent filesystem issues
    if len(sanitized) > 200:
        sanitized = sanitized[:200].strip()
    
    return sanitized or "Unknown"

def validate_audiobookbay_url(url: str) -> bool:
    """
    Validate if a URL is from AudiobookBay.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid AudiobookBay URL
    """
    if not url:
        return False
        
    # Check if URL is from the configured AudiobookBay hostname
    active_host = get_active_hostname()
    return any(m in url for m in MIRROR_HOSTNAMES) and url.startswith('http') and active_host.split(':')[0]

def get_scraper_stats() -> Dict[str, str]:
    """
    Get current scraper configuration and stats.
    
    Returns:
        Dict[str, str]: Configuration information
    """
    return {
        'active_hostname': get_active_hostname(),
        'configured_mirrors': ','.join(MIRROR_HOSTNAMES),
        'page_limit': str(PAGE_LIMIT),
        'timeout_seconds': str(REQUEST_TIMEOUT),
        'default_trackers_count': str(len(DEFAULT_TRACKERS)),
        'user_agent': DEFAULT_HEADERS['User-Agent'],
        'incognito_mode': str(INCOGNITO_MODE),
        'ua_rotation': str(ROTATE_USER_AGENT)
    }
