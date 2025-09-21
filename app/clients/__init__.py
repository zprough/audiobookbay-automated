"""
Download Client Package
Handles interactions with various torrent download clients.
"""

from .download_client import (
    add_torrent,
    get_torrents,
    get_client_info,
    get_download_client,
    BaseDownloadClient,
    QBittorrentManager,
    TransmissionManager,
    DelugeManager,
    DownloadClientError
)

__all__ = [
    'add_torrent',
    'get_torrents',
    'get_client_info',
    'get_download_client',
    'BaseDownloadClient',
    'QBittorrentManager',
    'TransmissionManager', 
    'DelugeManager',
    'DownloadClientError'
]
