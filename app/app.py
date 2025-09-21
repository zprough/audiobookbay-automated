"""
AudiobookBay Automated - Flask Web Application
Searches AudiobookBay for audiobooks and adds them to torrent clients.
"""

import os
from typing import Dict, Optional
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

# Import our custom modules
from api.torznab_api import torznab_bp
from scraper.audiobookbay_scraper import search_audiobookbay, extract_magnet_link, get_scraper_stats
from clients.download_client import add_torrent, get_torrents, get_client_info, DownloadClientError

app = Flask(__name__)

# Configure Flask app
app.secret_key = os.getenv('SECRET_KEY', 'audiobookbay-automated-secret-key-change-in-production')

# Register Torznab Blueprint
app.register_blueprint(torznab_bp)

# =============================================================================
# CONFIGURATION AND ENVIRONMENT VARIABLES
# =============================================================================

# Load environment variables from .env file (only if running locally)
# In containers, Docker Compose environment variables take precedence
load_dotenv(override=False)  # Don't override existing environment variables

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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Environment settings page route.
    
    GET: Display the settings form with current values
    POST: Save updated environment variables to .env file
    
    Returns:
        Rendered settings.html template with current settings or success/error messages
    """
    # Detect if running in container
    is_container = os.path.exists('/.dockerenv') or os.getenv('CONTAINER') == 'docker'
    
    if request.method == 'POST':
        try:
            # Get all form data
            settings_data = {}
            
            # Define all possible environment variables
            env_vars = [
                'ABB_HOSTNAME', 'PAGE_LIMIT', 'DOWNLOAD_CLIENT', 'DL_HOST', 'DL_PORT',
                'DL_USERNAME', 'DL_PASSWORD', 'DL_CATEGORY', 'SAVE_PATH_BASE',
                'NAV_LINK_NAME', 'NAV_LINK_URL', 'TORZNAB_API_KEY', 'TORZNAB_TITLE',
                'TORZNAB_DESCRIPTION', 'FLASK_DEBUG', 'DEV_PORT'
            ]
            
            # Collect form data
            for var in env_vars:
                value = request.form.get(var, '').strip()
                if value:  # Only save non-empty values
                    settings_data[var] = value
            
            # Write to .env file
            success = _write_env_file(settings_data)
            
            if success:
                print("[FLASK] Environment settings updated successfully")
                success_msg = "Settings saved successfully!"
                if is_container:
                    success_msg += " Note: Running in container mode - some changes may require container restart and Docker Compose environment variables will override these settings."
                    
                return render_template('settings.html', 
                                     settings=_get_current_settings(),
                                     success_message=success_msg,
                                     is_container=is_container)
            else:
                return render_template('settings.html', 
                                     settings=_get_current_settings(),
                                     error_message="Failed to save settings. Please check file permissions.",
                                     is_container=is_container)
                                     
        except Exception as e:
            print(f"[FLASK] Settings save error: {e}")
            return render_template('settings.html', 
                                 settings=_get_current_settings(),
                                 error_message=f"Error saving settings: {str(e)}",
                                 is_container=is_container)
    
    # GET request - display current settings
    return render_template('settings.html', 
                         settings=_get_current_settings(), 
                         is_container=is_container)

def _get_current_settings() -> Dict[str, Optional[str]]:
    """
    Get current environment variable values.
    
    Returns:
        Dict[str, Optional[str]]: Dictionary of current environment settings
    """
    return {
        'ABB_HOSTNAME': os.getenv('ABB_HOSTNAME'),
        'PAGE_LIMIT': os.getenv('PAGE_LIMIT'),
        'DOWNLOAD_CLIENT': os.getenv('DOWNLOAD_CLIENT'),
        'DL_HOST': os.getenv('DL_HOST'),
        'DL_PORT': os.getenv('DL_PORT'),
        'DL_USERNAME': os.getenv('DL_USERNAME'),
        'DL_PASSWORD': os.getenv('DL_PASSWORD'),
        'DL_CATEGORY': os.getenv('DL_CATEGORY'),
        'SAVE_PATH_BASE': os.getenv('SAVE_PATH_BASE'),
        'NAV_LINK_NAME': os.getenv('NAV_LINK_NAME'),
        'NAV_LINK_URL': os.getenv('NAV_LINK_URL'),
        'TORZNAB_API_KEY': os.getenv('TORZNAB_API_KEY'),
        'TORZNAB_TITLE': os.getenv('TORZNAB_TITLE'),
        'TORZNAB_DESCRIPTION': os.getenv('TORZNAB_DESCRIPTION'),
        'FLASK_DEBUG': os.getenv('FLASK_DEBUG'),
        'DEV_PORT': os.getenv('DEV_PORT'),
    }

def _write_env_file(settings: Dict[str, str]) -> bool:
    """
    Write environment variables to .env file.
    
    Args:
        settings (Dict[str, str]): Settings to write
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Detect if running in container
        is_container = os.path.exists('/.dockerenv') or os.getenv('CONTAINER') == 'docker'
        
        if is_container:
            # In container: try to write to mounted config volume
            config_dir = '/config'
            if os.path.exists(config_dir) and os.access(config_dir, os.W_OK):
                env_file_path = os.path.join(config_dir, '.env')
                print(f"[FLASK] Container mode: writing to {env_file_path}")
            else:
                # Fallback: write to app directory (will be lost on restart)
                env_file_path = os.path.join(os.path.dirname(__file__), '.env')
                print(f"[FLASK] Container mode: no writable config volume, using {env_file_path} (changes will be lost on restart)")
        else:
            # Local development: write to project root
            env_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            print(f"[FLASK] Local mode: writing to {env_file_path}")
        
        # Read existing .env file if it exists
        existing_settings = {}
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_settings[key.strip()] = value.strip()
        
        # Update with new settings
        existing_settings.update(settings)
        
        # Write back to file
        with open(env_file_path, 'w') as f:
            f.write("# AudiobookBay Automated Configuration\n")
            f.write("# Generated by web interface\n")
            if is_container:
                f.write("# Running in container mode\n")
                f.write("# Note: Docker Compose environment variables will override these settings\n")
            f.write("\n")
            
            # Group settings by category
            categories = {
                'AudiobookBay Settings': ['ABB_HOSTNAME', 'PAGE_LIMIT'],
                'Download Client Settings': ['DOWNLOAD_CLIENT', 'DL_HOST', 'DL_PORT', 
                                           'DL_USERNAME', 'DL_PASSWORD', 'DL_CATEGORY', 'SAVE_PATH_BASE'],
                'Navigation Settings': ['NAV_LINK_NAME', 'NAV_LINK_URL'],
                'Torznab API Settings': ['TORZNAB_API_KEY', 'TORZNAB_TITLE', 'TORZNAB_DESCRIPTION'],
                'Development Settings': ['FLASK_DEBUG', 'DEV_PORT']
            }
            
            for category, vars_list in categories.items():
                f.write(f"\n# {category}\n")
                for var in vars_list:
                    if var in existing_settings:
                        f.write(f"{var}={existing_settings[var]}\n")
        
        return True
        
    except Exception as e:
        print(f"[FLASK] Error writing .env file: {e}")
        return False

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
