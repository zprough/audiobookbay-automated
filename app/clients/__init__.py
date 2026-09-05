"""
Download Client Package
Handles interactions with various torrent download clients.
"""

from .download_client import (
    add_torrent,
    get_torrents,
    get_client_info,
    get_download_client,
    resolve_save_path,
    test_connection,
    rd_start_device_code,
    rd_get_device_credentials,
    rd_exchange_device_token,
    BaseDownloadClient,
    QBittorrentManager,
    TransmissionManager,
    DelugeManager,
    RealDebridManager,
    DownloadClientError
)
from .metadata_sidecar import write_sidecar, mark_complete
from .completion_tracker import track as track_completion

__all__ = [
    'add_torrent',
    'get_torrents',
    'get_client_info',
    'get_download_client',
    'resolve_save_path',
    'test_connection',
    'rd_start_device_code',
    'rd_get_device_credentials',
    'rd_exchange_device_token',
    'BaseDownloadClient',
    'QBittorrentManager',
    'TransmissionManager', 
    'DelugeManager',
    'RealDebridManager',
    'DownloadClientError',
    'write_sidecar',
    'mark_complete',
    'track_completion'
]
