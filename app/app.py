"""
AudiobookBay Automated - Flask application entry point.
Wires together the scraper, download clients, and Torznab API into the web UI.
"""

import os
import shutil
import threading

from dotenv import load_dotenv, find_dotenv, set_key
from flask import Flask, jsonify, redirect, render_template, request, url_for

from api import torznab_bp
from clients import (
    DownloadClientError,
    add_torrent,
    get_client_info,
    get_torrents,
    mark_complete,
    rd_exchange_device_token,
    rd_get_device_credentials,
    rd_start_device_code,
    resolve_save_path,
    test_connection,
    track_completion,
    write_sidecar,
)
from scraper import extract_magnet_link, search_audiobookbay


def _is_container_mode() -> bool:
    return os.path.exists("/.dockerenv") or os.getenv("CONTAINER") == "docker"


# Compose/system env vars always win (override=False); /config/.env supports
# persisted container settings, plain load_dotenv() walks up to the repo-root
# .env for local development (matches scripts/dev-local.sh's cwd=app/).
if _is_container_mode() and os.path.exists("/config/.env"):
    load_dotenv("/config/.env", override=False)
load_dotenv(override=False)

app = Flask(__name__)
app.register_blueprint(torznab_bp)

# Tracks save_paths currently mid-/send (guards against double-clicks racing
# each other before a staging folder even exists on disk).
_inflight_sends: set[str] = set()
_inflight_lock = threading.Lock()

# Keys the /settings page is allowed to view and persist.
SETTINGS_FIELDS = [
    "ABB_HOSTNAME",
    "DOWNLOAD_CLIENT",
    "DL_HOST",
    "DL_PORT",
    "DL_USERNAME",
    "DL_PASSWORD",
    "PAGE_LIMIT",
    "DL_CATEGORY",
    "SAVE_PATH_BASE",
    "DL_URL",
    "RD_DOWNLOADS_DIR",
    "RD_APP_TAG",
    "RD_TRACKED_TORRENTS_FILE",
    "RD_MIN_FILE_SIZE_MB",
    "RD_POLL_INTERVAL_SEC",
    "RD_EXCLUDE_EXTENSIONS",
    "RD_MAX_WAIT_SEC",
    "RD_AUTH_MODE",
    "RD_BASE_CLIENT_ID",
    "RD_API_TOKEN",
    "RD_CLIENT_ID",
    "RD_CLIENT_SECRET",
    "RD_ACCESS_TOKEN",
    "RD_REFRESH_TOKEN",
    "NAV_LINK_NAME",
    "NAV_LINK_URL",
    "TORZNAB_API_KEY",
    "TORZNAB_TITLE",
    "TORZNAB_DESCRIPTION",
    "FLASK_DEBUG",
    "DEV_PORT",
]


def _settings_env_path() -> str:
    if _is_container_mode():
        if os.path.isdir("/config") and os.access("/config", os.W_OK):
            return "/config/.env"
        return os.path.join(os.getcwd(), ".env")
    return find_dotenv(usecwd=True) or os.path.join(os.getcwd(), ".env")


@app.context_processor
def inject_nav_links():
    return {
        "nav_link_name": os.getenv("NAV_LINK_NAME"),
        "nav_link_url": os.getenv("NAV_LINK_URL"),
    }


@app.route("/")
def index():
    return redirect(url_for("search"))


@app.route("/search", methods=["GET", "POST"])
def search():
    query = None
    books = []
    error = None
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            try:
                books = search_audiobookbay(query)
            except Exception as exc:  # noqa: BLE001 - surface scraper failures to the UI
                error = f"Search failed: {exc}"
    return render_template("search.html", query=query, books=books, error=error)


def _cleanup_stale_send(save_path: str) -> None:
    """Remove a just-created staging folder if no real download data ever
    landed in it, so a legitimate retry after a client error isn't blocked
    by the duplicate-download check below."""
    try:
        if os.path.isdir(save_path) and set(os.listdir(save_path)) <= {".abb-meta.json", ".abb-complete"}:
            shutil.rmtree(save_path)
    except OSError:
        pass


@app.route("/send", methods=["POST"])
def send():
    payload = request.get_json(silent=True) or {}
    link = payload.get("link")
    title = payload.get("title")
    if not link or not title:
        return jsonify({"message": "Missing link or title"}), 400

    metadata = {
        "title": title,
        "cover": payload.get("cover"),
        "link": link,
        "categories": payload.get("categories"),
        "language": payload.get("language"),
    }

    try:
        save_path = resolve_save_path(title)
    except DownloadClientError as exc:
        return jsonify({"message": str(exc)}), 500

    # Reject if this exact title is already mid-flight or already has a
    # staging folder on disk (downloading, downloaded-but-unprocessed, etc.).
    with _inflight_lock:
        if save_path in _inflight_sends:
            return jsonify({"message": f"'{title}' is already being sent, please wait"}), 409
        if os.path.isdir(save_path) and os.listdir(save_path):
            return jsonify({
                "message": (
                    f"'{title}' has already been downloaded or is already in progress. "
                    "Check Status, or remove its folder to retry."
                )
            }), 409
        _inflight_sends.add(save_path)

    try:
        magnet = extract_magnet_link(link)
        if not magnet:
            return jsonify({"message": "Could not extract magnet link from AudiobookBay"}), 502

        # Written before queuing so the agent can find it as soon as files land,
        # regardless of which download client ends up handling the transfer.
        write_sidecar(save_path, metadata)

        ok = add_torrent(magnet, title)
        client_type = get_client_info().get("client_type", "").lower()
        if ok and client_type in ("realdebrid", "real-debrid"):
            # RealDebridManager.add_torrent() blocks until fully downloaded.
            mark_complete(save_path)
        elif ok:
            # Other clients are fire-and-forget; poll until the folder is stable.
            track_completion(save_path, metadata)
    except DownloadClientError as exc:
        _cleanup_stale_send(save_path)
        return jsonify({"message": str(exc)}), 500
    finally:
        with _inflight_lock:
            _inflight_sends.discard(save_path)

    if ok:
        client_type = get_client_info().get("client_type", "download client")
        return jsonify({"message": f"Added '{title}' to {client_type}"})
    _cleanup_stale_send(save_path)
    return jsonify({"message": f"Failed to add '{title}'"}), 500


@app.route("/status")
def status():
    try:
        torrents = get_torrents()
    except DownloadClientError as exc:
        return render_template("status.html", torrents=[], error=str(exc))
    return render_template("status.html", torrents=torrents)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    success_message = None
    error_message = None

    if request.method == "POST":
        env_path = _settings_env_path()
        try:
            for key in SETTINGS_FIELDS:
                if key not in request.form:
                    continue
                value = request.form.get(key, "")
                os.environ[key] = value
                set_key(env_path, key, value, quote_mode="never")
            success_message = f"Settings saved to {env_path}"
        except OSError as exc:
            error_message = f"Failed to save settings: {exc}"

    current_settings = {key: os.getenv(key) for key in SETTINGS_FIELDS}
    return render_template(
        "settings.html",
        settings=current_settings,
        is_container=_is_container_mode(),
        success_message=success_message,
        error_message=error_message,
    )


@app.route("/settings/realdebrid/device/start", methods=["POST"])
def rd_oauth_start():
    base_client_id = request.form.get("RD_BASE_CLIENT_ID") or os.getenv("RD_BASE_CLIENT_ID", "X245A4XAIBGVM")
    try:
        data = rd_start_device_code(base_client_id)
    except DownloadClientError as exc:
        return jsonify({"message": str(exc)}), 502
    return jsonify(data)


@app.route("/settings/realdebrid/device/complete", methods=["POST"])
def rd_oauth_complete():
    payload = request.get_json(silent=True) or {}
    device_code = payload.get("device_code")
    base_client_id = payload.get("base_client_id") or os.getenv("RD_BASE_CLIENT_ID", "X245A4XAIBGVM")
    if not device_code:
        return jsonify({"message": "device_code is required"}), 400

    try:
        creds = rd_get_device_credentials(base_client_id, device_code)
        token = rd_exchange_device_token(creds["client_id"], creds["client_secret"], device_code)
    except DownloadClientError as exc:
        return jsonify({"message": str(exc)}), 502

    env_path = _settings_env_path()
    updates = {
        "RD_CLIENT_ID": creds["client_id"],
        "RD_CLIENT_SECRET": creds["client_secret"],
        "RD_ACCESS_TOKEN": token["access_token"],
        "RD_REFRESH_TOKEN": token.get("refresh_token", ""),
        "RD_AUTH_MODE": "oauth",
    }
    for key, value in updates.items():
        os.environ[key] = value
        set_key(env_path, key, value, quote_mode="never")

    return jsonify({"message": "Real-Debrid authorization completed"})


@app.route("/settings/test-download-client", methods=["POST"])
def test_download_client_route():
    try:
        ok = test_connection()
        info = get_client_info()
    except DownloadClientError as exc:
        return jsonify({"message": str(exc)}), 502

    if ok:
        return jsonify({"message": f"Connected to {info['client_type']}"})
    return jsonify({"message": f"Could not connect to {info['client_type']}"}), 502


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.getenv("DEV_PORT", "5078"))
    app.run(host="0.0.0.0", port=port, debug=debug)
