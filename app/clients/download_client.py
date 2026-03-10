"""
Download Client Manager Module
Handles interactions with various torrent download clients.
"""

import os
import time
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from qbittorrentapi import Client as QBittorrentClient
from transmission_rpc import Client as TransmissionClient
from deluge_web_client import DelugeWebClient
from urllib.parse import urlparse

from scraper.audiobookbay_scraper import sanitize_title

# =============================================================================
# CONFIGURATION
# =============================================================================

def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _load_download_config() -> Dict[str, Any]:
    download_client = os.getenv("DOWNLOAD_CLIENT")
    dl_url = os.getenv("DL_URL")

    if dl_url:
        parsed_url = urlparse(dl_url)
        dl_scheme = parsed_url.scheme
        dl_host = parsed_url.hostname
        dl_port = parsed_url.port
    else:
        dl_scheme = os.getenv("DL_SCHEME", "http")
        dl_host = os.getenv("DL_HOST")
        dl_port_str = os.getenv("DL_PORT")
        dl_port = int(dl_port_str) if dl_port_str else None
        if dl_host and dl_port:
            dl_url = f"{dl_scheme}://{dl_host}:{dl_port}"

    return {
        "DOWNLOAD_CLIENT": download_client,
        "DL_URL": dl_url,
        "DL_SCHEME": dl_scheme,
        "DL_HOST": dl_host,
        "DL_PORT": dl_port,
        "DL_USERNAME": os.getenv("DL_USERNAME"),
        "DL_PASSWORD": os.getenv("DL_PASSWORD"),
        "DL_CATEGORY": os.getenv("DL_CATEGORY", "Audiobookbay-Audiobooks"),
        "SAVE_PATH_BASE": os.getenv("SAVE_PATH_BASE"),
        "RD_AUTH_MODE": (os.getenv("RD_AUTH_MODE") or "oauth").strip().lower(),
        "RD_API_TOKEN": os.getenv("RD_API_TOKEN"),
        "RD_BASE_CLIENT_ID": os.getenv("RD_BASE_CLIENT_ID", "X245A4XAIBGVM"),
        "RD_CLIENT_ID": os.getenv("RD_CLIENT_ID"),
        "RD_CLIENT_SECRET": os.getenv("RD_CLIENT_SECRET"),
        "RD_ACCESS_TOKEN": os.getenv("RD_ACCESS_TOKEN"),
        "RD_REFRESH_TOKEN": os.getenv("RD_REFRESH_TOKEN"),
        "RD_DOWNLOADS_DIR": os.getenv("RD_DOWNLOADS_DIR", "/downloads"),
        "RD_APP_TAG": (os.getenv("RD_APP_TAG") or "abb-automated").strip(),
        "RD_TRACKED_TORRENTS_FILE": os.getenv("RD_TRACKED_TORRENTS_FILE"),
        "RD_MIN_FILE_SIZE_MB": _float_env("RD_MIN_FILE_SIZE_MB", 25.0),
        "RD_EXCLUDE_EXTENSIONS": os.getenv("RD_EXCLUDE_EXTENSIONS", ".nfo,.txt,.jpg,.jpeg,.png"),
        "RD_POLL_INTERVAL_SEC": _int_env("RD_POLL_INTERVAL_SEC", 5),
        "RD_MAX_WAIT_SEC": _int_env("RD_MAX_WAIT_SEC", 900),
    }


def _parse_extensions(csv_text: str) -> set[str]:
    values = set()
    for raw in csv_text.split(','):
        cleaned = raw.strip().lower()
        if not cleaned:
            continue
        if not cleaned.startswith('.'):
            cleaned = f".{cleaned}"
        values.add(cleaned)
    return values


OAUTH_BASE_URL = "https://api.real-debrid.com/oauth/v2"


def rd_start_device_code(base_client_id: str) -> Dict[str, Any]:
    response = requests.get(
        f"{OAUTH_BASE_URL}/device/code",
        params={"client_id": base_client_id, "new_credentials": "yes"},
        timeout=20,
    )
    if response.status_code >= 400:
        raise DownloadClientError(f"Real-Debrid device/code failed: {response.status_code} {response.text}")
    data = response.json()
    if "device_code" not in data:
        raise DownloadClientError("Real-Debrid device/code response missing device_code")
    return data


def rd_get_device_credentials(base_client_id: str, device_code: str) -> Dict[str, Any]:
    response = requests.get(
        f"{OAUTH_BASE_URL}/device/credentials",
        params={"client_id": base_client_id, "code": device_code},
        timeout=20,
    )
    if response.status_code >= 400:
        raise DownloadClientError(f"Real-Debrid device/credentials failed: {response.status_code} {response.text}")
    data = response.json()
    if "client_id" not in data or "client_secret" not in data:
        raise DownloadClientError("Real-Debrid credentials not ready yet")
    return data


def rd_exchange_device_token(client_id: str, client_secret: str, code: str) -> Dict[str, Any]:
    response = requests.post(
        f"{OAUTH_BASE_URL}/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "http://oauth.net/grant_type/device/1.0",
        },
        timeout=20,
    )
    if response.status_code >= 400:
        raise DownloadClientError(f"Real-Debrid token exchange failed: {response.status_code} {response.text}")
    data = response.json()
    if "access_token" not in data:
        raise DownloadClientError("Real-Debrid token exchange did not return access_token")
    return data

# =============================================================================
# DOWNLOAD CLIENT CLASSES
# =============================================================================

class DownloadClientError(Exception):
    """Custom exception for download client errors."""
    pass

class BaseDownloadClient:
    """Base class for download clients."""
    
    def add_torrent(self, magnet_link: str, save_path: str) -> bool:
        """Add a torrent to the download client."""
        raise NotImplementedError
    
    def get_torrents(self) -> List[Dict[str, Any]]:
        """Get list of torrents from the download client."""
        raise NotImplementedError
    
    def test_connection(self) -> bool:
        """Test connection to the download client."""
        raise NotImplementedError

class QBittorrentManager(BaseDownloadClient):
    """qBittorrent download client manager."""
    
    def __init__(self, config: Dict[str, Any]):
        self.host = config["DL_HOST"]
        self.port = config["DL_PORT"]
        self.username = config["DL_USERNAME"]
        self.password = config["DL_PASSWORD"]
        self.category = config["DL_CATEGORY"]
    
    def _get_client(self) -> QBittorrentClient:
        """Get authenticated qBittorrent client."""
        client = QBittorrentClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )
        client.auth_log_in()
        return client
    
    def add_torrent(self, magnet_link: str, save_path: str) -> bool:
        """Add a torrent to qBittorrent."""
        try:
            client = self._get_client()
            client.torrents_add(
                urls=magnet_link,
                save_path=save_path,
                category=self.category
            )
            print(f"[DOWNLOAD] Added torrent to qBittorrent: {save_path}")
            return True
        except Exception as e:
            print(f"[DOWNLOAD] qBittorrent error: {e}")
            raise DownloadClientError(f"Failed to add torrent to qBittorrent: {e}")
    
    def get_torrents(self) -> List[Dict[str, Any]]:
        """Get torrents from qBittorrent."""
        try:
            client = self._get_client()
            torrents = client.torrents_info(category=self.category)
            return [
                {
                    'name': torrent.name,
                    'progress': round(torrent.progress * 100, 2),
                    'state': torrent.state,
                    'size': f"{torrent.total_size / (1024 * 1024):.2f} MB"
                }
                for torrent in torrents
            ]
        except Exception as e:
            print(f"[DOWNLOAD] qBittorrent get_torrents error: {e}")
            raise DownloadClientError(f"Failed to get torrents from qBittorrent: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to qBittorrent."""
        try:
            client = self._get_client()
            # Try to get application version as connection test
            _ = client.app.version
            return True
        except Exception as e:
            print(f"[DOWNLOAD] qBittorrent connection test failed: {e}")
            return False

class TransmissionManager(BaseDownloadClient):
    """Transmission download client manager."""
    
    def __init__(self, config: Dict[str, Any]):
        self.host = config["DL_HOST"]
        self.port = config["DL_PORT"]
        self.protocol = config["DL_SCHEME"]
        self.username = config["DL_USERNAME"]
        self.password = config["DL_PASSWORD"]
    
    def _get_client(self) -> TransmissionClient:
        """Get authenticated Transmission client."""
        return TransmissionClient(
            host=self.host,
            port=self.port,
            protocol=self.protocol,
            username=self.username,
            password=self.password
        )
    
    def add_torrent(self, magnet_link: str, save_path: str) -> bool:
        """Add a torrent to Transmission."""
        try:
            client = self._get_client()
            client.add_torrent(magnet_link, download_dir=save_path)
            print(f"[DOWNLOAD] Added torrent to Transmission: {save_path}")
            return True
        except Exception as e:
            print(f"[DOWNLOAD] Transmission error: {e}")
            raise DownloadClientError(f"Failed to add torrent to Transmission: {e}")
    
    def get_torrents(self) -> List[Dict[str, Any]]:
        """Get torrents from Transmission."""
        try:
            client = self._get_client()
            torrents = client.get_torrents()
            return [
                {
                    'name': torrent.name,
                    'progress': round(torrent.progress, 2),
                    'state': torrent.status,
                    'size': f"{torrent.total_size / (1024 * 1024):.2f} MB"
                }
                for torrent in torrents
            ]
        except Exception as e:
            print(f"[DOWNLOAD] Transmission get_torrents error: {e}")
            raise DownloadClientError(f"Failed to get torrents from Transmission: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to Transmission."""
        try:
            client = self._get_client()
            # Try to get session stats as connection test
            _ = client.get_session()
            return True
        except Exception as e:
            print(f"[DOWNLOAD] Transmission connection test failed: {e}")
            return False

class DelugeManager(BaseDownloadClient):
    """Deluge WebUI download client manager."""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config["DL_URL"]
        self.password = config["DL_PASSWORD"]
        self.category = config["DL_CATEGORY"]
    
    def _get_client(self) -> DelugeWebClient:
        """Get authenticated Deluge client."""
        client = DelugeWebClient(url=self.url, password=self.password)
        client.login()
        return client
    
    def add_torrent(self, magnet_link: str, save_path: str) -> bool:
        """Add a torrent to Deluge."""
        try:
            client = self._get_client()
            client.add_torrent_magnet(
                magnet_link,
                save_directory=save_path,
                label=self.category
            )
            print(f"[DOWNLOAD] Added torrent to Deluge: {save_path}")
            return True
        except Exception as e:
            print(f"[DOWNLOAD] Deluge error: {e}")
            raise DownloadClientError(f"Failed to add torrent to Deluge: {e}")
    
    def get_torrents(self) -> List[Dict[str, Any]]:
        """Get torrents from Deluge."""
        try:
            client = self._get_client()
            torrents = client.get_torrents_status(
                filter_dict={"label": self.category},
                keys=["name", "state", "progress", "total_size"],
            )
            return [
                {
                    "name": torrent["name"],
                    "progress": round(torrent["progress"], 2),
                    "state": torrent["state"],
                    "size": f"{torrent['total_size'] / (1024 * 1024):.2f} MB",
                }
                for k, torrent in torrents.result.items()
            ]
        except Exception as e:
            print(f"[DOWNLOAD] Deluge get_torrents error: {e}")
            raise DownloadClientError(f"Failed to get torrents from Deluge: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to Deluge."""
        try:
            client = self._get_client()
            # Try to get daemon version as connection test
            _ = client.get_daemon_version()
            return True
        except Exception as e:
            print(f"[DOWNLOAD] Deluge connection test failed: {e}")
            return False


class RealDebridManager(BaseDownloadClient):
    """Real-Debrid download client manager."""

    def __init__(self, config: Dict[str, Any]):
        self.api_base = "https://api.real-debrid.com/rest/1.0"
        self.oauth_base = OAUTH_BASE_URL
        self.auth_mode = config["RD_AUTH_MODE"]
        self.api_token = config["RD_API_TOKEN"]
        self.base_client_id = config["RD_BASE_CLIENT_ID"]
        self.client_id = config["RD_CLIENT_ID"]
        self.client_secret = config["RD_CLIENT_SECRET"]
        self.access_token = config["RD_ACCESS_TOKEN"]
        self.refresh_token = config["RD_REFRESH_TOKEN"]
        self.downloads_dir = config["RD_DOWNLOADS_DIR"] or "/downloads"
        self.app_tag = config["RD_APP_TAG"] or "abb-automated"
        tracked_file = config.get("RD_TRACKED_TORRENTS_FILE")
        self.tracked_torrents_file = Path(tracked_file) if tracked_file else Path(self.downloads_dir) / ".abb-rd-tracked-torrents.json"
        self._tracked_lock = threading.Lock()
        self.min_file_size_bytes = int(float(config["RD_MIN_FILE_SIZE_MB"]) * 1024 * 1024)
        self.exclude_extensions = _parse_extensions(config["RD_EXCLUDE_EXTENSIONS"])
        self.poll_interval_sec = max(2, int(config["RD_POLL_INTERVAL_SEC"]))
        self.max_wait_sec = max(30, int(config["RD_MAX_WAIT_SEC"]))

    def _load_tracked_torrents(self) -> Dict[str, Any]:
        default_payload = {"version": 1, "tags": {}}
        if not self.tracked_torrents_file.exists():
            return default_payload

        try:
            with open(self.tracked_torrents_file, "r", encoding="utf-8") as tracked_file:
                data = json.load(tracked_file)
                if not isinstance(data, dict):
                    return default_payload
                if "tags" not in data or not isinstance(data.get("tags"), dict):
                    data["tags"] = {}
                return data
        except Exception as e:
            print(f"[DOWNLOAD] Failed to read RD tracked torrents file: {e}")
            return default_payload

    def _save_tracked_torrents(self, payload: Dict[str, Any]) -> None:
        self.tracked_torrents_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tracked_torrents_file, "w", encoding="utf-8") as tracked_file:
            json.dump(payload, tracked_file, indent=2, sort_keys=True)

    def _track_torrent(self, torrent_id: str, title: str) -> None:
        if not torrent_id:
            return

        with self._tracked_lock:
            payload = self._load_tracked_torrents()
            tags = payload.setdefault("tags", {})
            tag_entries = tags.setdefault(self.app_tag, {})
            tag_entries[str(torrent_id)] = {
                "title": title,
                "added_at": int(time.time()),
            }
            self._save_tracked_torrents(payload)

    def _get_tracked_ids(self) -> set[str]:
        with self._tracked_lock:
            payload = self._load_tracked_torrents()
        tags = payload.get("tags") or {}
        tag_entries = tags.get(self.app_tag)
        if isinstance(tag_entries, dict):
            return set(tag_entries.keys())
        return set()

    def _refresh_access_token(self) -> str:
        if not self.client_id or not self.client_secret or not self.refresh_token:
            raise DownloadClientError("Real-Debrid OAuth refresh requires RD_CLIENT_ID, RD_CLIENT_SECRET, and RD_REFRESH_TOKEN")

        token_data = rd_exchange_device_token(self.client_id, self.client_secret, self.refresh_token)
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        os.environ["RD_ACCESS_TOKEN"] = self.access_token or ""
        os.environ["RD_REFRESH_TOKEN"] = self.refresh_token or ""

        if not self.access_token:
            raise DownloadClientError("Real-Debrid refresh returned no access token")
        return self.access_token

    def _get_access_token(self) -> str:
        if self.auth_mode == "token":
            if not self.api_token:
                raise DownloadClientError("RD_API_TOKEN is required when RD_AUTH_MODE=token")
            return self.api_token

        if self.access_token:
            return self.access_token

        return self._refresh_access_token()

    def _request(self, method: str, endpoint: str, retry_on_auth: bool = True, **kwargs: Any) -> requests.Response:
        token = self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        response = requests.request(
            method,
            f"{self.api_base}{endpoint}",
            headers=headers,
            timeout=30,
            **kwargs,
        )

        if response.status_code == 401 and retry_on_auth and self.auth_mode != "token":
            refreshed = self._refresh_access_token()
            headers["Authorization"] = f"Bearer {refreshed}"
            response = requests.request(
                method,
                f"{self.api_base}{endpoint}",
                headers=headers,
                timeout=30,
                **kwargs,
            )

        return response

    def _request_json(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        response = self._request(method, endpoint, **kwargs)
        if response.status_code >= 400:
            raise DownloadClientError(f"Real-Debrid API {endpoint} failed: {response.status_code} {response.text}")
        return response.json() if response.text else {}

    def _add_magnet(self, magnet_link: str) -> str:
        data = self._request_json("POST", "/torrents/addMagnet", data={"magnet": magnet_link})
        torrent_id = data.get("id")
        if not torrent_id:
            raise DownloadClientError("Real-Debrid addMagnet returned no torrent id")
        return torrent_id

    def _get_torrent_info(self, torrent_id: str) -> Dict[str, Any]:
        return self._request_json("GET", f"/torrents/info/{torrent_id}")

    def _select_files(self, torrent_id: str, files_value: str) -> None:
        response = self._request("POST", f"/torrents/selectFiles/{torrent_id}", data={"files": files_value})
        if response.status_code >= 400:
            raise DownloadClientError(f"Real-Debrid selectFiles failed: {response.status_code} {response.text}")

    def _unrestrict_link(self, link: str) -> Dict[str, Any]:
        return self._request_json("POST", "/unrestrict/link", data={"link": link})

    def _wait_for_status(self, torrent_id: str, target_statuses: set[str]) -> Dict[str, Any]:
        deadline = time.time() + self.max_wait_sec
        last_info: Dict[str, Any] = {}

        while time.time() <= deadline:
            info = self._get_torrent_info(torrent_id)
            last_info = info
            status = (info.get("status") or "").lower()

            if status in target_statuses:
                return info

            if status in {"magnet_error", "error", "virus", "dead"}:
                raise DownloadClientError(f"Real-Debrid torrent failed with status '{status}'")

            time.sleep(self.poll_interval_sec)

        raise DownloadClientError(
            f"Real-Debrid torrent timed out after {self.max_wait_sec}s (last status: {last_info.get('status', 'unknown')})"
        )

    def _is_file_allowed(self, file_path: str, size: int) -> bool:
        if size < self.min_file_size_bytes:
            return False
        lower_path = file_path.lower()
        for ext in self.exclude_extensions:
            if lower_path.endswith(ext):
                return False
        return True

    def _choose_file_ids(self, files: List[Dict[str, Any]]) -> str:
        if not files:
            return "all"

        preferred_ids: List[str] = []
        fallback_ids: List[str] = []

        for file_info in files:
            file_id = file_info.get("id")
            if file_id is None:
                continue
            file_path = str(file_info.get("path") or "")
            file_size = int(file_info.get("bytes") or 0)

            if self._is_file_allowed(file_path, file_size):
                preferred_ids.append(str(file_id))

            lower_path = file_path.lower()
            if not any(lower_path.endswith(ext) for ext in self.exclude_extensions):
                fallback_ids.append(str(file_id))

        if preferred_ids:
            return ",".join(preferred_ids)
        if fallback_ids:
            return ",".join(fallback_ids)

        all_ids = [str(file_info.get("id")) for file_info in files if file_info.get("id") is not None]
        return ",".join(all_ids) if all_ids else "all"

    def _download_file(self, url: str, target_dir: Path, filename: str) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = sanitize_title(filename).replace('/', '_').replace('\\', '_')
        output_path = target_dir / safe_name

        with requests.get(url, stream=True, timeout=120) as response:
            if response.status_code >= 400:
                raise DownloadClientError(f"Failed to download file: {response.status_code} {response.text}")
            with open(output_path, "wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output_file.write(chunk)

    def add_torrent(self, magnet_link: str, save_path: str) -> bool:
        torrent_id = self._add_magnet(magnet_link)
        self._track_torrent(torrent_id, Path(save_path).name)

        info = self._wait_for_status(
            torrent_id,
            {"waiting_files_selection", "queued", "downloading", "downloaded", "magnet_conversion"},
        )

        current_status = (info.get("status") or "").lower()
        if current_status == "waiting_files_selection" or not info.get("links"):
            selected_files = self._choose_file_ids(info.get("files") or [])
            self._select_files(torrent_id, selected_files)

        downloaded_info = self._wait_for_status(torrent_id, {"downloaded"})
        host_links = downloaded_info.get("links") or []
        if not host_links:
            raise DownloadClientError("Real-Debrid torrent completed with no host links")

        title_segment = sanitize_title(Path(save_path).name) if save_path else "audiobook"
        target_dir = Path(self.downloads_dir) / title_segment

        for link in host_links:
            unrestricted = self._unrestrict_link(link)
            download_url = unrestricted.get("download")
            filename = unrestricted.get("filename") or f"{torrent_id}.bin"
            if not download_url:
                raise DownloadClientError("Real-Debrid unrestrict/link returned no download URL")
            self._download_file(download_url, target_dir, filename)

        return True

    def get_torrents(self) -> List[Dict[str, Any]]:
        response = self._request("GET", "/torrents")
        if response.status_code >= 400:
            raise DownloadClientError(f"Failed to list Real-Debrid torrents: {response.status_code} {response.text}")

        torrents = response.json() if response.text else []
        tracked_ids = self._get_tracked_ids()
        if not tracked_ids:
            return []

        normalized: List[Dict[str, Any]] = []
        for torrent in torrents:
            torrent_id = str(torrent.get("id") or "")
            if torrent_id not in tracked_ids:
                continue

            bytes_total = int(torrent.get("bytes") or 0)
            progress = float(torrent.get("progress") or 0)
            normalized.append(
                {
                    "name": torrent.get("filename", "Unknown"),
                    "progress": round(progress, 2),
                    "state": torrent.get("status", "unknown"),
                    "size": f"{bytes_total / (1024 * 1024):.2f} MB" if bytes_total else "Unknown",
                }
            )

        return normalized

    def test_connection(self) -> bool:
        try:
            response = self._request("GET", "/user")
            return response.status_code == 200
        except Exception as e:
            print(f"[DOWNLOAD] Real-Debrid connection test failed: {e}")
            return False

# =============================================================================
# DOWNLOAD CLIENT FACTORY
# =============================================================================

def get_download_client() -> BaseDownloadClient:
    """
    Get the appropriate download client based on configuration.
    
    Returns:
        BaseDownloadClient: Configured download client instance
        
    Raises:
        DownloadClientError: If no valid client is configured
    """
    config = _load_download_config()
    download_client = config["DOWNLOAD_CLIENT"]

    if not download_client:
        raise DownloadClientError("No download client configured. Set DOWNLOAD_CLIENT environment variable.")
    
    client_type = download_client.lower()
    
    if client_type == 'qbittorrent':
        return QBittorrentManager(config)
    elif client_type == 'transmission':
        return TransmissionManager(config)
    elif client_type in ['delugeweb', 'deluge']:
        return DelugeManager(config)
    elif client_type in ['realdebrid', 'real-debrid']:
        return RealDebridManager(config)
    else:
        raise DownloadClientError(f"Unsupported download client: {download_client}")

def add_torrent(magnet_link: str, title: str) -> bool:
    """
    Add a torrent to the configured download client.
    
    Args:
        magnet_link (str): Magnet link for the torrent
        title (str): Title for organizing the download
        
    Returns:
        bool: True if successful
        
    Raises:
        DownloadClientError: If adding the torrent fails
    """
    config = _load_download_config()
    client_type = (config["DOWNLOAD_CLIENT"] or "").lower()
    save_path_base = config["SAVE_PATH_BASE"]

    if not save_path_base and client_type in ['realdebrid', 'real-debrid']:
        save_path_base = config["RD_DOWNLOADS_DIR"] or "/downloads"

    if not save_path_base:
        raise DownloadClientError("SAVE_PATH_BASE not configured")
    
    save_path = f"{save_path_base}/{sanitize_title(title)}"
    
    client = get_download_client()
    return client.add_torrent(magnet_link, save_path)

def get_torrents() -> List[Dict[str, Any]]:
    """
    Get list of torrents from the configured download client.
    
    Returns:
        List[Dict[str, Any]]: List of torrent information
        
    Raises:
        DownloadClientError: If getting torrents fails
    """
    client = get_download_client()
    return client.get_torrents()

def test_connection() -> bool:
    """
    Test connection to the configured download client.
    
    Returns:
        bool: True if connection successful
    """
    try:
        client = get_download_client()
        return client.test_connection()
    except Exception as e:
        print(f"[DOWNLOAD] Connection test failed: {e}")
        return False

def get_client_info() -> Dict[str, str]:
    """
    Get information about the configured download client.
    
    Returns:
        Dict[str, str]: Client configuration information
    """
    config = _load_download_config()
    return {
        'client_type': config["DOWNLOAD_CLIENT"] or 'None',
        'host': config["DL_HOST"] or 'None',
        'port': str(config["DL_PORT"]) if config["DL_PORT"] else 'None',
        'url': config["DL_URL"] or 'None',
        'category': config["DL_CATEGORY"],
        'save_path_base': config["SAVE_PATH_BASE"] or 'None',
        'rd_auth_mode': config["RD_AUTH_MODE"],
        'rd_downloads_dir': config["RD_DOWNLOADS_DIR"],
        'rd_app_tag': config["RD_APP_TAG"],
    }
