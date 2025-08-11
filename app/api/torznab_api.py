"""
Torznab API Module for AudiobookBay Automated
Provides a Torznab-compatible API endpoint for integration with applications like Lazylibrarian.
"""

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional, Any
from flask import Blueprint, request, Response
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote

# Import our custom modules
from scraper import search_audiobookbay, extract_magnet_link

# Create Blueprint for Torznab API
torznab_bp = Blueprint('torznab', __name__, url_prefix='/torznab')

# =============================================================================
# TORZNAB CONFIGURATION
# =============================================================================

# Torznab API Configuration
TORZNAB_API_KEY: str = os.getenv("TORZNAB_API_KEY", "audiobookbay-automated")
TORZNAB_TITLE: str = os.getenv("TORZNAB_TITLE", "AudiobookBay Automated")
TORZNAB_DESCRIPTION: str = os.getenv("TORZNAB_DESCRIPTION", "AudiobookBay search via Torznab API")

# AudiobookBay Configuration (imported from main app)
ABB_HOSTNAME: str = os.getenv("ABB_HOSTNAME", "audiobookbay.lu")
PAGE_LIMIT: int = int(os.getenv("PAGE_LIMIT", 5))

# =============================================================================
# TORZNAB HELPER FUNCTIONS
# =============================================================================

def validate_api_key(provided_key: str) -> bool:
    """
    Validate the provided API key against the configured key.
    
    Args:
        provided_key (str): API key provided in the request
        
    Returns:
        bool: True if valid, False otherwise
    """
    return provided_key == TORZNAB_API_KEY

def create_error_response(error_code: int, description: str) -> Response:
    """
    Create a Torznab-formatted XML error response.
    
    Args:
        error_code (int): Torznab error code
        description (str): Error description
        
    Returns:
        Response: Flask Response object with XML content
    """
    root = ET.Element("error")
    root.set("code", str(error_code))
    root.set("description", description)
    
    xml_str = ET.tostring(root, encoding='unicode')
    return Response(xml_str, content_type='application/xml')

def create_caps_response() -> Response:
    """
    Create a Torznab capabilities response.
    
    Returns:
        Response: Flask Response object with XML capabilities
    """
    root = ET.Element("caps")
    
    # Server info
    server = ET.SubElement(root, "server")
    server.set("version", "1.0")
    server.set("title", TORZNAB_TITLE)
    server.set("strapline", TORZNAB_DESCRIPTION)
    server.set("email", "")
    server.set("url", "")
    server.set("image", "")
    
    # Limits
    limits = ET.SubElement(root, "limits")
    limits.set("max", "100")
    limits.set("default", "20")
    
    # Searching capabilities
    searching = ET.SubElement(root, "searching")
    search = ET.SubElement(searching, "search")
    search.set("available", "yes")
    search.set("supportedParams", "q")
    
    # Categories (Audiobooks)
    categories = ET.SubElement(root, "categories")
    category = ET.SubElement(categories, "category")
    category.set("id", "3030")
    category.set("name", "Audiobooks")
    
    xml_str = ET.tostring(root, encoding='unicode')
    return Response(xml_str, content_type='application/xml')

def search_audiobookbay_for_torznab(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search AudiobookBay and return results formatted for Torznab.
    
    Args:
        query (str): Search query string
        limit (int): Maximum number of results to return
        
    Returns:
        List[Dict[str, Any]]: List of search results with Torznab-compatible fields
    """
    # Use the main scraper function
    results = search_audiobookbay(query, max_pages=3)  # Limit pages for API performance
    
    torznab_results = []
    
    for result in results[:limit]:  # Limit to requested number of results
        try:
            # Create a unique GUID
            guid = f"audiobookbay-{abs(hash(result['link']))}"
            
            # Create display name from title
            display_name = result['title']
            
            # Current timestamp for pub_date
            pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            torznab_result = {
                'title': display_name,
                'guid': guid,
                'link': result['link'],
                'comments': result['link'],
                'pub_date': pub_date,
                'category': "Audiobooks",
                'size': "0",  # AudiobookBay doesn't always show size
                'description': display_name
            }
            
            torznab_results.append(torznab_result)
            
        except Exception as e:
            print(f"[TORZNAB] Error processing result: {e}")
            continue
    
    return torznab_results

def extract_magnet_for_torznab(details_url: str) -> Optional[str]:
    """
    Extract magnet link from AudiobookBay details page for Torznab.
    Just a wrapper around the main scraper function.
    
    Args:
        details_url (str): URL of the AudiobookBay details page
        
    Returns:
        Optional[str]: Magnet link or None if extraction fails
    """
    return extract_magnet_link(details_url)

def create_search_response(results: List[Dict[str, Any]]) -> Response:
    """
    Create a Torznab-formatted XML search response.
    
    Args:
        results (List[Dict[str, Any]]): Search results
        
    Returns:
        Response: Flask Response object with XML search results
    """
    root = ET.Element("rss")
    root.set("version", "2.0")
    root.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    root.set("xmlns:torznab", "http://torznab.com/schemas/2015/feed")
    
    channel = ET.SubElement(root, "channel")
    
    # Channel info
    ET.SubElement(channel, "title").text = TORZNAB_TITLE
    ET.SubElement(channel, "description").text = TORZNAB_DESCRIPTION
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    # Add items
    for result in results:
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "title").text = result['title']
        ET.SubElement(item, "guid").text = result['guid']
        ET.SubElement(item, "link").text = result['link']
        ET.SubElement(item, "comments").text = result['comments']
        ET.SubElement(item, "pubDate").text = result['pub_date']
        ET.SubElement(item, "category").text = result['category']
        ET.SubElement(item, "description").text = result['description']
        
        # Torznab-specific attributes
        size_attr = ET.SubElement(item, "torznab:attr")
        size_attr.set("name", "size")
        size_attr.set("value", str(result['size']))
        
        category_attr = ET.SubElement(item, "torznab:attr")
        category_attr.set("name", "category")
        category_attr.set("value", "3030")  # Audiobooks category
    
    xml_str = ET.tostring(root, encoding='unicode')
    return Response(xml_str, content_type='application/xml')

# =============================================================================
# TORZNAB API ROUTES
# =============================================================================

@torznab_bp.route('/api')
def torznab_api():
    """
    Main Torznab API endpoint.
    
    Handles 'caps' and 'search' functions based on the 't' parameter.
    
    Returns:
        Response: XML response based on the requested function
    """
    # Get parameters
    api_key = request.args.get('apikey', '')
    function = request.args.get('t', '')
    
    # Validate API key for all requests except caps
    if function != 'caps' and not validate_api_key(api_key):
        return create_error_response(100, "Invalid API key")
    
    if function == 'caps':
        return create_caps_response()
    
    elif function == 'search':
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 20)), 100)  # Cap at 100
        
        if not query:
            return create_error_response(200, "Missing query parameter")
        
        try:
            results = search_audiobookbay_for_torznab(query, limit)
            return create_search_response(results)
        except Exception as e:
            print(f"[TORZNAB] Search error: {e}")
            return create_error_response(300, "Search failed")
    
    else:
        return create_error_response(202, "Unknown or unsupported function")

@torznab_bp.route('/download/<path:guid>')
def torznab_download(guid: str):
    """
    Handle torrent download requests by GUID.
    
    Args:
        guid (str): Unique identifier for the torrent
        
    Returns:
        Response: Magnet link redirect or error
    """
    api_key = request.args.get('apikey', '')
    
    if not validate_api_key(api_key):
        return create_error_response(100, "Invalid API key")
    
    # For now, return an error since we need the original link to extract magnet
    # This could be enhanced by storing GUIDs and their corresponding links
    return create_error_response(201, "Download not implemented - use magnet links from search results")

# =============================================================================
# BLUEPRINT INFO ROUTE
# =============================================================================

@torznab_bp.route('/')
def torznab_info():
    """
    Provide information about the Torznab API endpoint.
    
    Returns:
        str: HTML page with API information
    """
    info_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{TORZNAB_TITLE} - Torznab API</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .code {{ background: #f4f4f4; padding: 10px; border-radius: 4px; }}
            .endpoint {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>{TORZNAB_TITLE}</h1>
        <p>{TORZNAB_DESCRIPTION}</p>
        
        <h2>API Endpoints</h2>
        
        <div class="endpoint">
            <h3>Capabilities</h3>
            <div class="code">GET /torznab/api?t=caps</div>
            <p>Returns the capabilities of this Torznab indexer.</p>
        </div>
        
        <div class="endpoint">
            <h3>Search</h3>
            <div class="code">GET /torznab/api?t=search&apikey={{API_KEY}}&q={{QUERY}}&limit={{LIMIT}}</div>
            <p>Search for audiobooks. Requires API key authentication.</p>
        </div>
        
        <h2>Configuration for Lazylibrarian</h2>
        <ul>
            <li><strong>URL:</strong> http://your-server:port/torznab/api</li>
            <li><strong>API Key:</strong> {TORZNAB_API_KEY}</li>
            <li><strong>Categories:</strong> 3030 (Audiobooks)</li>
        </ul>
        
        <h2>Environment Variables</h2>
        <ul>
            <li><strong>TORZNAB_API_KEY:</strong> Set your API key (default: audiobookbay-automated)</li>
            <li><strong>TORZNAB_TITLE:</strong> Indexer title (default: AudiobookBay Automated)</li>
            <li><strong>TORZNAB_DESCRIPTION:</strong> Indexer description</li>
        </ul>
    </body>
    </html>
    """
    return info_html
