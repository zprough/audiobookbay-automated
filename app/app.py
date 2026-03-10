"""
AudiobookBay Automated - Flask Web Application
Searches AudiobookBay for audiobooks and adds them to torrent clients.
"""

import os
import threading
from queue import Queue
from datetime import datetime
from uuid import uuid4
from typing import Dict, Optional, Any, List
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

# Import our custom modules
from api.torznab_api import torznab_bp
from scraper.audiobookbay_scraper import search_audiobookbay, extract_magnet_link, get_scraper_stats
from clients.download_client import (
    add_torrent,
    get_torrents,
    get_client_info,
    test_connection as test_download_client_connection,
    rd_start_device_code,
    rd_get_device_credentials,
    rd_exchange_device_token,
    DownloadClientError,
)

app = Flask(__name__)

RD_DEVICE_SESSIONS: Dict[str, Dict[str, str]] = {}
RD_JOB_QUEUE: Queue[dict] = Queue()
RD_JOBS: Dict[str, Dict[str, Any]] = {}
RD_JOBS_LOCK = threading.Lock()

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

    scraper_stats = get_scraper_stats()
    hostname = scraper_stats.get('active_hostname') or scraper_stats.get('hostname') or 'unavailable'
    print("SCRAPER CONFIGURATION:")
    print(f"  ABB_HOSTNAME: {hostname}")
    print(f"  PAGE_LIMIT: {scraper_stats.get('page_limit', 'unknown')}")
    print(f"  DEFAULT_TRACKERS: {scraper_stats.get('default_trackers_count', 'unknown')}")

    client_info = get_client_info()
    print("DOWNLOAD CLIENT CONFIGURATION:")
    print(f"  CLIENT_TYPE: {client_info['client_type']}")
    print(f"  HOST: {client_info['host']}")
    print(f"  PORT: {client_info['port']}")
    print(f"  CATEGORY: {client_info['category']}")
    print(f"  SAVE_PATH: {client_info['save_path_base']}")

    print("FLASK APP CONFIGURATION:")
    print(f"  NAV_LINK_NAME: {NAV_LINK_NAME}")
    print(f"  NAV_LINK_URL: {NAV_LINK_URL}")
    print("=" * 60)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _is_realdebrid_client() -> bool:
    client_type = (os.getenv("DOWNLOAD_CLIENT") or "").strip().lower()
    return client_type in {"realdebrid", "real-debrid"}


def _build_rd_job_status_rows() -> List[Dict[str, Any]]:
    with RD_JOBS_LOCK:
        sorted_jobs = sorted(RD_JOBS.values(), key=lambda item: item.get("created_at", ""), reverse=True)

    rows: List[Dict[str, Any]] = []
    for job in sorted_jobs:
        rows.append(
            {
                "name": f"[RD Job] {job.get('title', 'Unknown')}",
                "progress": job.get("progress", 0),
                "state": job.get("state", "queued"),
                "size": job.get("size", "N/A"),
            }
        )

    return rows


def _run_rd_job(job_id: str, magnet_link: str, title: str) -> None:
    with RD_JOBS_LOCK:
        if job_id not in RD_JOBS:
            return
        RD_JOBS[job_id]["state"] = "running"
        RD_JOBS[job_id]["progress"] = 5
        RD_JOBS[job_id]["updated_at"] = _now_iso()

    try:
        add_torrent(magnet_link, title)
        with RD_JOBS_LOCK:
            RD_JOBS[job_id]["state"] = "completed"
            RD_JOBS[job_id]["progress"] = 100
            RD_JOBS[job_id]["updated_at"] = _now_iso()
    except Exception as e:
        with RD_JOBS_LOCK:
            RD_JOBS[job_id]["state"] = f"error: {str(e)}"
            RD_JOBS[job_id]["progress"] = 100
            RD_JOBS[job_id]["updated_at"] = _now_iso()


def _rd_job_worker() -> None:
    while True:
        job = RD_JOB_QUEUE.get()
        try:
            _run_rd_job(job["job_id"], job["magnet_link"], job["title"])
        except Exception as e:
            print(f"[RD] Worker unexpected error: {e}")
        finally:
            RD_JOB_QUEUE.task_done()


def _ensure_rd_worker_started() -> None:
    if getattr(_ensure_rd_worker_started, "_started", False):
        return
    worker = threading.Thread(target=_rd_job_worker, name="rd-job-worker", daemon=True)
    worker.start()
    _ensure_rd_worker_started._started = True


_ensure_rd_worker_started()

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
    current_query = ''
    try:
        if request.method == 'POST':  # Form submitted
            query = request.form.get('query', '').strip()
            if query:  # Only search if the query is not empty
                # Convert to lowercase for consistency
                query = query.lower()
                current_query = query
                books = search_audiobookbay(query)
                print(f"[FLASK] Search completed: '{query}' returned {len(books)} results")
            else:
                print("[FLASK] Empty search query received")

        return render_template('search.html', books=books, query=current_query)
        
    except Exception as e:
        print(f"[FLASK] Search error: {e}")
        return render_template('search.html', books=books, query=current_query, error=f"Search failed: {str(e)}")

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
            if _is_realdebrid_client():
                job_id = str(uuid4())
                with RD_JOBS_LOCK:
                    RD_JOBS[job_id] = {
                        "job_id": job_id,
                        "title": title,
                        "state": "queued",
                        "progress": 0,
                        "size": "N/A",
                        "created_at": _now_iso(),
                        "updated_at": _now_iso(),
                    }

                RD_JOB_QUEUE.put({"job_id": job_id, "magnet_link": magnet_link, "title": title})
                print(f"[FLASK] Queued Real-Debrid job: {title} ({job_id})")
                return jsonify({
                    'message': 'Real-Debrid job queued. The audiobook will download to /downloads in the background.',
                    'job_id': job_id,
                })

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
        rd_jobs = _build_rd_job_status_rows() if _is_realdebrid_client() else []
        torrents = rd_jobs + get_torrents()
        print(f"[FLASK] Status page: showing {len(torrents)} torrents")
        return render_template('status.html', torrents=torrents)
        
    except DownloadClientError as e:
        print(f"[FLASK] Download client error on status: {e}")
        fallback_torrents = _build_rd_job_status_rows() if _is_realdebrid_client() else []
        return render_template('status.html', torrents=fallback_torrents)
        
    except Exception as e:
        print(f"[FLASK] Status error: {e}")
        error_message = "Status is temporarily unavailable."
        return render_template('status.html', torrents=[], error=error_message)


@app.route('/settings/test-download-client', methods=['POST'])
def settings_test_download_client():
    """Test current download client connection from settings page."""
    try:
        is_ok = test_download_client_connection()
        if is_ok:
            return jsonify({'message': 'Connection successful'})
        return jsonify({'message': 'Connection failed. Check your client settings and credentials.'}), 500
    except Exception as e:
        return jsonify({'message': f'Connection test error: {str(e)}'}), 500

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
                'DL_USERNAME', 'DL_PASSWORD', 'DL_CATEGORY', 'SAVE_PATH_BASE', 'DL_URL',
                'NAV_LINK_NAME', 'NAV_LINK_URL', 'TORZNAB_API_KEY', 'TORZNAB_TITLE',
                'TORZNAB_DESCRIPTION', 'FLASK_DEBUG', 'DEV_PORT',
                'RD_AUTH_MODE', 'RD_API_TOKEN', 'RD_BASE_CLIENT_ID', 'RD_CLIENT_ID',
                'RD_CLIENT_SECRET', 'RD_ACCESS_TOKEN', 'RD_REFRESH_TOKEN',
                'RD_DOWNLOADS_DIR', 'RD_MIN_FILE_SIZE_MB', 'RD_EXCLUDE_EXTENSIONS',
                'RD_POLL_INTERVAL_SEC', 'RD_MAX_WAIT_SEC'
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
        'DOWNLOAD_CLIENT': os.getenv('DOWNLOAD_CLIENT', 'realdebrid'),
        'DL_HOST': os.getenv('DL_HOST'),
        'DL_PORT': os.getenv('DL_PORT'),
        'DL_URL': os.getenv('DL_URL'),
        'DL_USERNAME': os.getenv('DL_USERNAME'),
        'DL_PASSWORD': os.getenv('DL_PASSWORD'),
        'DL_CATEGORY': os.getenv('DL_CATEGORY'),
        'SAVE_PATH_BASE': os.getenv('SAVE_PATH_BASE'),
        'RD_AUTH_MODE': os.getenv('RD_AUTH_MODE', 'oauth'),
        'RD_API_TOKEN': os.getenv('RD_API_TOKEN'),
        'RD_BASE_CLIENT_ID': os.getenv('RD_BASE_CLIENT_ID', 'X245A4XAIBGVM'),
        'RD_CLIENT_ID': os.getenv('RD_CLIENT_ID'),
        'RD_CLIENT_SECRET': os.getenv('RD_CLIENT_SECRET'),
        'RD_ACCESS_TOKEN': os.getenv('RD_ACCESS_TOKEN'),
        'RD_REFRESH_TOKEN': os.getenv('RD_REFRESH_TOKEN'),
        'RD_DOWNLOADS_DIR': os.getenv('RD_DOWNLOADS_DIR', '/downloads'),
        'RD_MIN_FILE_SIZE_MB': os.getenv('RD_MIN_FILE_SIZE_MB', '25'),
        'RD_EXCLUDE_EXTENSIONS': os.getenv('RD_EXCLUDE_EXTENSIONS', '.nfo,.txt,.jpg,.jpeg,.png'),
        'RD_POLL_INTERVAL_SEC': os.getenv('RD_POLL_INTERVAL_SEC', '5'),
        'RD_MAX_WAIT_SEC': os.getenv('RD_MAX_WAIT_SEC', '900'),
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
                                           'DL_USERNAME', 'DL_PASSWORD', 'DL_CATEGORY', 'SAVE_PATH_BASE', 'DL_URL'],
                'Real-Debrid Settings': [
                    'RD_AUTH_MODE', 'RD_API_TOKEN', 'RD_BASE_CLIENT_ID', 'RD_CLIENT_ID',
                    'RD_CLIENT_SECRET', 'RD_ACCESS_TOKEN', 'RD_REFRESH_TOKEN',
                    'RD_DOWNLOADS_DIR', 'RD_MIN_FILE_SIZE_MB', 'RD_EXCLUDE_EXTENSIONS',
                    'RD_POLL_INTERVAL_SEC', 'RD_MAX_WAIT_SEC'
                ],
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


@app.route('/settings/realdebrid/device/start', methods=['POST'])
def start_realdebrid_device_auth():
    """Start Real-Debrid OAuth2 device authorization flow."""
    try:
        payload = request.get_json(silent=True) if request.is_json else {}
        base_client_id = request.form.get('RD_BASE_CLIENT_ID') or (payload or {}).get('RD_BASE_CLIENT_ID')
        if not base_client_id:
            base_client_id = os.getenv('RD_BASE_CLIENT_ID', 'X245A4XAIBGVM')

        data = rd_start_device_code(base_client_id)
        device_code = data.get('device_code')
        if not device_code:
            return jsonify({'message': 'Real-Debrid did not return a device code'}), 500

        RD_DEVICE_SESSIONS[device_code] = {'base_client_id': base_client_id}

        return jsonify({
            'message': 'Device authorization started',
            'device_code': device_code,
            'user_code': data.get('user_code'),
            'verification_url': data.get('verification_url'),
            'interval': data.get('interval', 5),
            'expires_in': data.get('expires_in', 1800),
            'base_client_id': base_client_id,
        })

    except DownloadClientError as e:
        return jsonify({'message': str(e)}), 500
    except Exception as e:
        return jsonify({'message': f'Failed to start Real-Debrid auth: {str(e)}'}), 500


@app.route('/settings/realdebrid/device/complete', methods=['POST'])
def complete_realdebrid_device_auth():
    """Complete Real-Debrid OAuth2 device authorization flow."""
    try:
        data = request.get_json(silent=True) or request.form
        device_code = (data.get('device_code') or '').strip()
        base_client_id = (data.get('base_client_id') or '').strip()

        if not device_code:
            return jsonify({'message': 'Missing device_code'}), 400

        if not base_client_id:
            session_data = RD_DEVICE_SESSIONS.get(device_code, {})
            base_client_id = session_data.get('base_client_id') or os.getenv('RD_BASE_CLIENT_ID', 'X245A4XAIBGVM')

        try:
            credentials = rd_get_device_credentials(base_client_id, device_code)
        except DownloadClientError:
            return jsonify({'message': 'Authorization pending. Complete code entry on Real-Debrid and try again.'}), 409

        token_data = rd_exchange_device_token(
            credentials['client_id'],
            credentials['client_secret'],
            device_code,
        )

        updates = {
            'RD_AUTH_MODE': 'oauth',
            'RD_BASE_CLIENT_ID': base_client_id,
            'RD_CLIENT_ID': credentials.get('client_id', ''),
            'RD_CLIENT_SECRET': credentials.get('client_secret', ''),
            'RD_ACCESS_TOKEN': token_data.get('access_token', ''),
            'RD_REFRESH_TOKEN': token_data.get('refresh_token', ''),
        }

        _write_env_file(updates)
        for key, value in updates.items():
            os.environ[key] = value

        RD_DEVICE_SESSIONS.pop(device_code, None)

        return jsonify({'message': 'Real-Debrid authorization successful'})

    except DownloadClientError as e:
        return jsonify({'message': str(e)}), 500
    except Exception as e:
        return jsonify({'message': f'Failed to complete Real-Debrid auth: {str(e)}'}), 500

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
