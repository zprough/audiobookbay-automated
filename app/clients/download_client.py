"""
Download Client Manager Module
Handles interactions with various torrent download clients.
"""

import os
from typing import List, Dict, Any, Optional
from qbittorrentapi import Client as QBittorrentClient
from transmission_rpc import Client as TransmissionClient
from deluge_web_client import DelugeWebClient
from urllib.parse import urlparse

# =============================================================================
# CONFIGURATION
# =============================================================================

# Download Client Configuration (from environment)
DOWNLOAD_CLIENT: Optional[str] = os.getenv("DOWNLOAD_CLIENT")
DL_URL: Optional[str] = os.getenv("DL_URL")

# Parse DL_URL if provided, otherwise use individual components
if DL_URL:
    parsed_url = urlparse(DL_URL)
    DL_SCHEME: str = parsed_url.scheme
    DL_HOST: Optional[str] = parsed_url.hostname
    DL_PORT: Optional[int] = parsed_url.port
else:
    DL_SCHEME = os.getenv("DL_SCHEME", "http")
    DL_HOST = os.getenv("DL_HOST")
    dl_port_str = os.getenv("DL_PORT")
    DL_PORT = int(dl_port_str) if dl_port_str else None

    # Construct DL_URL for Deluge if components are provided
    if DL_HOST and DL_PORT:
        DL_URL = f"{DL_SCHEME}://{DL_HOST}:{DL_PORT}"

# Download Client Authentication
DL_USERNAME: Optional[str] = os.getenv("DL_USERNAME")
DL_PASSWORD: Optional[str] = os.getenv("DL_PASSWORD")
DL_CATEGORY: str = os.getenv("DL_CATEGORY", "Audiobookbay-Audiobooks")
SAVE_PATH_BASE: Optional[str] = os.getenv("SAVE_PATH_BASE")

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
    
    def __init__(self):
        self.host = DL_HOST
        self.port = DL_PORT
        self.username = DL_USERNAME
        self.password = DL_PASSWORD
        self.category = DL_CATEGORY
    
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
    
    def __init__(self):
        self.host = DL_HOST
        self.port = DL_PORT
        self.protocol = DL_SCHEME
        self.username = DL_USERNAME
        self.password = DL_PASSWORD
    
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
    
    def __init__(self):
        self.url = DL_URL
        self.password = DL_PASSWORD
        self.category = DL_CATEGORY
    
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
    if not DOWNLOAD_CLIENT:
        raise DownloadClientError("No download client configured. Set DOWNLOAD_CLIENT environment variable.")
    
    client_type = DOWNLOAD_CLIENT.lower()
    
    if client_type == 'qbittorrent':
        return QBittorrentManager()
    elif client_type == 'transmission':
        return TransmissionManager()
    elif client_type in ['delugeweb', 'deluge']:
        return DelugeManager()
    else:
        raise DownloadClientError(f"Unsupported download client: {DOWNLOAD_CLIENT}")

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
    from audiobookbay_scraper import sanitize_title
    
    if not SAVE_PATH_BASE:
        raise DownloadClientError("SAVE_PATH_BASE not configured")
    
    save_path = f"{SAVE_PATH_BASE}/{sanitize_title(title)}"
    
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
    return {
        'client_type': DOWNLOAD_CLIENT or 'None',
        'host': DL_HOST or 'None',
        'port': str(DL_PORT) if DL_PORT else 'None',
        'url': DL_URL or 'None',
        'category': DL_CATEGORY,
        'save_path_base': SAVE_PATH_BASE or 'None'
    }
