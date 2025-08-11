"""
AudiobookBay Scraper Module
Handles all AudiobookBay scraping, magnet link extraction, and data processing.
"""

import os
import re
import requests
import base64
import html as htmllib
from typing import List, Dict, Optional, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

# AudiobookBay Configuration (from environment)
ABB_HOSTNAME: str = os.getenv("ABB_HOSTNAME", "audiobookbay.lu")
PAGE_LIMIT: int = int(os.getenv("PAGE_LIMIT", 5))

# Request headers to mimic a real browser
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

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

def _scrape_search_page(query: str, page: int) -> List[Dict[str, str]]:
    """
    Scrape a single search results page from AudiobookBay.
    
    Args:
        query (str): Search query string
        page (int): Page number to scrape
        
    Returns:
        List[Dict[str, str]]: List of results from this page
    """
    url = f"https://{ABB_HOSTNAME}/page/{page}/?s={query.replace(' ', '+')}&cat=undefined%2Cundefined"
    
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[SCRAPER] Failed to fetch page {page}. Status Code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_posts_from_page(soup)
        
    except requests.exceptions.RequestException as e:
        print(f"[SCRAPER] Network error on page {page}: {e}")
        return []
    except Exception as e:
        print(f"[SCRAPER] Unexpected error on page {page}: {e}")
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

    posts = []

    for i, div in enumerate(post_divs):
        try:
            # If post has class re-ab then decode it
            if 're-ab' in div.get('class', []):
                base64_encoded_text = div.text.strip()
                decoded_bytes = base64.b64decode(base64_encoded_text)
                decoded_text = decoded_bytes.decode('utf-8', errors='replace')
                posts.append(decoded_text)
            else:
                posts.append(div.decode_contents())
        except Exception as e:
            print(f"Decoding failed {i}: {e}")
    
    for post in post_divs:
        try:
            # Get the raw HTML content for detailed parsing
            post_html = str(post)
            
            # Parse the comprehensive post information
            post_data = _parse_post_details(post_html)
            
            # Only add posts with valid titles and links
            if post_data.get('title') and post_data.get('link'):
                results.append(post_data)
            
        except Exception as e:
            print(f"[SCRAPER] Error extracting post: {e}")
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
    def parse_posts_to_df(html_list):
    rows = [parse_item(item) for item in html_list]
    df = pd.DataFrame(rows)
    if "posted_date" in df and df["posted_date"].notna().any():
        df["posted_date_sort"] = pd.to_datetime(df["posted_date"], errors="coerce")
        df = df.sort_values("posted_date_sort", ascending=False).drop(columns=["posted_date_sort"])
    return df
    Args:
        html_snippet (str): HTML content of the post
        
    Returns:
        Dict[str, Any]: Comprehensive post information
    """
    if not html_snippet.strip().startswith("<"):
        html_snippet = f"<div>{htmllib.escape(html_snippet)}</div>"

    soup = BeautifulSoup(html_snippet, "html.parser")
    base_url = f"https://{ABB_HOSTNAME}"

    # Extract title and post URL
    a_title = soup.select_one(".postTitle h2 a") or soup.find("a", rel="bookmark")
    title = a_title.get_text(strip=True) if a_title else None
    
    # Handle href extraction safely
    href = None
    if a_title:
        try:
            href = a_title.get("href")  # type: ignore
        except:
            pass
    post_url = urljoin(base_url, str(href)) if href else None

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
    image_url = "/static/images/default_cover.jpg"  # default
    if img:
        try:
            cover_src = img.get("src")  # type: ignore
            if cover_src:
                cover_src = str(cover_src)  # ensure string
                if cover_src.startswith('//'):
                    image_url = 'https:' + cover_src
                elif cover_src.startswith('/'):
                    image_url = urljoin(base_url, cover_src)
                else:
                    image_url = cover_src
        except:
            pass  # use default

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
        "cover": image_url,  # Keep 'cover' for compatibility
        "categories": categories,
        "language": language,
        "keywords": keywords,
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
        response = requests.get(details_url, headers=DEFAULT_HEADERS, timeout=15)
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
    return ABB_HOSTNAME in url and url.startswith('http')

def get_scraper_stats() -> Dict[str, str]:
    """
    Get current scraper configuration and stats.
    
    Returns:
        Dict[str, str]: Configuration information
    """
    return {
        'hostname': ABB_HOSTNAME,
        'page_limit': str(PAGE_LIMIT),
        'default_trackers_count': str(len(DEFAULT_TRACKERS)),
        'user_agent': DEFAULT_HEADERS['User-Agent']
    }
