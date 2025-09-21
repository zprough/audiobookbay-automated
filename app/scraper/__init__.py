"""
AudiobookBay Scraper Package
Handles all scraping and data processing for AudiobookBay.
"""

from .audiobookbay_scraper import (
    search_audiobookbay,
    extract_magnet_link,
    get_scraper_stats,
    sanitize_title
)

__all__ = [
    'search_audiobookbay',
    'extract_magnet_link', 
    'get_scraper_stats',
    'sanitize_title'
]
