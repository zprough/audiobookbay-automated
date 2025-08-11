"""
AudiobookBay Automated - Flask Web Application
Searches AudiobookBay for audiobooks and adds them to torrent clients.
"""

import os
from typing import Dict, Optional
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv

# Import our custom modules
from api import torznab_bp
from scraper import search_audiobookbay, extract_magnet_link, get_scraper_stats
from clients import add_torrent, get_torrents, get_client_info, DownloadClientError

app = Flask(__name__)

# Register Torznab Blueprint
app.register_blueprint(torznab_bp)

# =============================================================================
# CONFIGURATION AND ENVIRONMENT VARIABLES
# =============================================================================

# Load environment variables from .env file
load_dotenv()

# Custom Navigation Link Configuration (only used by Flask app)
NAV_LINK_NAME: Optional[str] = os.getenv("NAV_LINK_NAME")
NAV_LINK_URL: Optional[str] = os.getenv("NAV_LINK_URL")

# =============================================================================
# CONFIGURATION LOGGING
# =============================================================================

def log_configuration() -> None:
    """Log the current configuration settings for debugging purposes."""
    print("=" * 60)
    print("AUDIOBOOKBAY AUTOMATED - CONFIGURATION")
    print("=" * 60)
    
    # Scraper configuration
    scraper_stats = get_scraper_stats()
    print("SCRAPER CONFIGURATION:")
    print(f"  ABB_HOSTNAME: {scraper_stats['hostname']}")
    print(f"  PAGE_LIMIT: {scraper_stats['page_limit']}")
    print(f"  DEFAULT_TRACKERS: {scraper_stats['default_trackers_count']}")
    
    # Download client configuration
    client_info = get_client_info()
    print("DOWNLOAD CLIENT CONFIGURATION:")
    print(f"  CLIENT_TYPE: {client_info['client_type']}")
    print(f"  HOST: {client_info['host']}")
    print(f"  PORT: {client_info['port']}")
    print(f"  CATEGORY: {client_info['category']}")
    print(f"  SAVE_PATH: {client_info['save_path_base']}")
    
    # Flask app configuration
    print("FLASK APP CONFIGURATION:")
    print(f"  NAV_LINK_NAME: {NAV_LINK_NAME}")
    print(f"  NAV_LINK_URL: {NAV_LINK_URL}")
    print("=" * 60)

# Log configuration on startup
log_configuration()

# =============================================================================
# FLASK CONTEXT PROCESSORS
# =============================================================================

@app.context_processor
def inject_nav_link() -> Dict[str, Optional[str]]:
    """
    Inject navigation link variables into all templates.
    
    Returns:
        Dict[str, Optional[str]]: Dictionary containing nav_link_name and nav_link_url
    """
    return {
        'nav_link_name': NAV_LINK_NAME,
        'nav_link_url': NAV_LINK_URL
    }

# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route('/', methods=['GET', 'POST'])
def search():
    """
    Main search page route.
    
    GET: Display the search form
    POST: Process search query and display results
    
    Returns:
        Rendered search.html template with search results or errors
    """
    books = []
    try:
        if request.method == 'POST':  # Form submitted
            query = request.form.get('query', '').strip()
            if query:  # Only search if the query is not empty
                # Convert to lowercase for consistency
                query = query.lower()
                books = search_audiobookbay(query)
                print(f"[FLASK] Search completed: '{query}' returned {len(books)} results")
            else:
                print("[FLASK] Empty search query received")
                
        return render_template('search.html', books=books)
        
    except Exception as e:
        print(f"[FLASK] Search error: {e}")
        return render_template('search.html', books=books, error=f"Search failed: {str(e)}")

@app.route('/send', methods=['POST'])
def send():
    """
    API endpoint to send a magnet link to the configured torrent client.
    
    Expects JSON payload with 'link' (details URL) and 'title' fields.
    
    Returns:
        JSON response indicating success or failure
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'Invalid JSON payload'}), 400
            
        details_url = data.get('link')
        title = data.get('title')
        
        if not details_url or not title:
            return jsonify({'message': 'Missing link or title in request'}), 400

        # Extract magnet link from AudiobookBay page
        magnet_link = extract_magnet_link(details_url)
        if not magnet_link:
            return jsonify({'message': 'Failed to extract magnet link from page'}), 500

        # Add torrent to download client
        try:
            add_torrent(magnet_link, title)
            print(f"[FLASK] Successfully added torrent: {title}")
            return jsonify({
                'message': 'Download added successfully! The audiobook will appear in your download client.'
            })
        except DownloadClientError as e:
            print(f"[FLASK] Download client error: {e}")
            return jsonify({'message': f'Download client error: {str(e)}'}), 500

    except Exception as e:
        print(f"[FLASK] Send error: {e}")
        return jsonify({'message': f'Unexpected error: {str(e)}'}), 500

@app.route('/status')
def status():
    """
    Status page route showing current torrent downloads.
    
    Displays active torrents from the configured download client
    with progress, state, and size information.
    
    Returns:
        Rendered status.html template with torrent list or error message
    """
    try:
        torrents = get_torrents()
        print(f"[FLASK] Status page: showing {len(torrents)} torrents")
        return render_template('status.html', torrents=torrents)
        
    except DownloadClientError as e:
        print(f"[FLASK] Download client error on status: {e}")
        error_message = f"Download client error: {str(e)}"
        return render_template('status.html', torrents=[], error=error_message)
        
    except Exception as e:
        print(f"[FLASK] Status error: {e}")
        error_message = f"Failed to fetch torrent status: {str(e)}"
        return render_template('status.html', torrents=[], error=error_message)

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == '__main__':
    """
    Start the Flask development server.
    
    Uses environment variables:
    - FLASK_DEBUG: Enable debug mode (default: False)
    - DEV_PORT: Port number for development server (default: 5078)
    """
    # Enable debug mode when running locally
    debug_mode: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Use different port for development
    port: int = int(os.getenv('DEV_PORT', '5078'))
    
    print(f"🚀 Starting Flask server on port {port} (debug={'ON' if debug_mode else 'OFF'})")
    print(f"🌐 Web interface: http://localhost:{port}")
    print(f"📡 Torznab API: http://localhost:{port}/torznab/api")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
