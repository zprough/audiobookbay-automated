"""
AudiobookBay Scraper Module
Handles all AudiobookBay scraping, magnet link extraction, and data processing.
"""

import os
import re
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote

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
        List[Dict[str, str]]: List of extracted posts
    """
    results = []
    
    for post in soup.select('.post'):
        try:
            # Extract title and link
            title_element = post.select_one('.postTitle > h2 > a')
            if not title_element:
                continue
                
            title = title_element.text.strip()
            if not title:
                continue
                
            # Construct full link
            href = title_element.get('href', '')
            if not href:
                continue
                
            link = f"https://{ABB_HOSTNAME}{href}"
            
            # Extract cover image
            img_element = post.select_one('img')
            if img_element and img_element.get('src'):
                cover_src = img_element.get('src')
                if isinstance(cover_src, str):
                    # Ensure cover is a full URL
                    if cover_src.startswith('//'):
                        cover = 'https:' + cover_src
                    elif cover_src.startswith('/'):
                        cover = f"https://{ABB_HOSTNAME}{cover_src}"
                    else:
                        cover = cover_src
                else:
                    cover = "/static/images/default-cover.jpg"
            else:
                cover = "/static/images/default-cover.jpg"
            
            results.append({
                'title': title,
                'link': link,
                'cover': cover
            })
            
        except Exception as e:
            print(f"[SCRAPER] Error extracting post: {e}")
            continue
    
    return results

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
