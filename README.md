
# AudiobookBay Automated

AudiobookBay Automated is a Sonarr/Radarr-style automation tool for audiobooks. It lets you search [**AudioBook Bay**](https://audiobookbay.lu/) and send magnet links to a designated **Deluge, qBittorrent, Transmission, or Real-Debrid** client, then automatically organizes, tags, and moves completed downloads into your final audiobook library (e.g. for [**Audiobookshelf**](https://www.audiobookshelf.org/) to pick up).

## How It Works
- **Search Results**: Users search for audiobooks. The app grabs results from AudioBook Bay and displays results with the **title** and **cover image**, along with two action links:
  1. **More Details**: Opens the audiobook's page on AudioBook Bay for additional information.
  2. **Download to Server**: Sends the audiobook to your configured torrent client for downloading.

- **Magnet Link Generation**: When a user selects "Download to Server," the app generates a magnet link from the infohash displayed on AudioBook Bay and sends it to the torrent client. Along with the magnet link, the app assigns:
  - A **category label** for organizational purposes.
  - A **staging save location** for downloaded files (`SAVE_PATH_BASE`).

- **Automated Organizing (Agent)**: A background agent process watches the staging folder for completed downloads, then converts/merges audio files as needed, tags metadata (title/author/cover), renames, and moves the finished audiobook into your final library folder (`LIBRARY_DIR`) — the same folder your Audiobookshelf instance should scan. Items that fail processing are moved to `FAILED_DIR` for manual review instead of being silently dropped.


## Features
- **Search Audiobook Bay**: Easily search for audiobooks by title or keywords.
- **View Details**: Displays book titles and covers with quickly links to the full details on AudioBook Bay.
- **Basic Download Status Page**: Monitor the download status of items in your torrent client that share the specified category assigned.
- **No AudioBook Bay Account Needed**: The app automatically generates magnet links from the displayed infohashes and push them to your torrent client for downloading.
- **Automatic Folder Organization**: Once a download finishes, the built-in agent process converts/tags/renames the audiobook and moves it into your library folder, organized into `Author/Title` subfolders, making it easy for [**Audiobookshelf**](https://www.audiobookshelf.org/) to automatically add completed downloads to its library.



## Why Use This?
AudiobookBay Downloader provides a simple and user-friendly interface for users to download audiobooks without on their own and import them into your libary. 

---

## Installation

### Prerequisites
- **Deluge, qBittorrent or Transmission** (with the WebUI enabled)
- **Docker** (optional, for containerized deployments)

### Environment Variables
The app uses environment variables to configure its behavior. Below are the required variables:

```env
DL_SCHEME=http
DL_HOST=192.168.xxx.xxx        # IP or hostname of your qBittorrent or Transmission instance
DL_PORT=8080                   # torrent WebUI port
DL_USERNAME=YOUR_USER          # torrent username
DL_PASSWORD=YOUR_PASSWORD      # torrent password
DL_CATEGORY=abb-downloader     # torrent category for downloads
SAVE_PATH_BASE=/downloads      # Staging path where downloads land; the agent watches this (INPUT_DIR) and organizes finished books into LIBRARY_DIR
ABB_HOSTNAME='audiobookbay.is' # Default
PAGE_LIMIT=5                   # Defaults to 5 if not set, more than this may probably rate limit.
ABB_TIMEOUT=8                  # (Seconds) network timeout and mirror probe timeout (optional)
ABB_DNS_BYPASS=true            # (Optional) Force ABB DNS lookups to custom resolvers (default true)
ABB_DNS_SERVERS=1.1.1.1,8.8.8.8 # (Optional) DNS resolvers used only for ABB mirror hostnames
ABB_DNS_LIFETIME=2.5           # (Optional) DNS query timeout/lifetime in seconds
INCOGNITO_MODE=true            # (Optional) Enable per-request incognito style headers (no persistent cookies, cache bust)
ROTATE_USER_AGENT=true         # (Optional) Rotate user-agent each request (default true)
DISABLE_CACHE_BUST=false       # (Optional) If true, disables the _cb cache-busting query string
RD_APP_TAG=abb-automated       # (Real-Debrid optional) Tag used to track app-origin torrents for status filtering
RD_TRACKED_TORRENTS_FILE=/downloads/.abb-rd-tracked-torrents.json # (Real-Debrid optional) Tracked torrent ID storage file

# Agent (organize/tag/move) settings
INPUT_DIR=/downloads           # Staging folder the agent watches (same as SAVE_PATH_BASE)
LIBRARY_DIR=/audiobooks        # Final library folder the agent moves organized books into (point Audiobookshelf here)
FAILED_DIR=/failed             # Items that fail processing land here for manual review
WORK_DIR=/work                 # Internal scratch space used during conversion
ENABLE_PICARD=false            # Picard is a GUI app with no reliable headless mode; leave off
ENABLE_LLM=false                # Optional Ollama-assisted title/author decisions
ENABLE_AUDIOBOOKSHELF_SCAN=false # Optional: trigger an Audiobookshelf library scan after organizing
AUDIOBOOKSHELF_URL=http://audiobookshelf:80
AUDIOBOOKSHELF_TOKEN=
```
Mirror Fallback:

If the primary AudiobookBay domain is down or blocked, the application will automatically try the following mirrors (in this order) until one responds:

1. Value of `ABB_HOSTNAME` (if provided and not already in list)
2. `audiobookbay.lu`
3. `audiobookbay.fi`
4. `audiobookbay.is`
5. `theaudiobookbay.se`

The first responsive mirror is cached for subsequent requests. If a request later fails, the cache is cleared and mirrors are retried. You can override the initial preferred domain via `ABB_HOSTNAME`.

Incognito / Header Randomization:

When `INCOGNITO_MODE` is enabled the scraper will:
- Rotate user-agents (if `ROTATE_USER_AGENT` true)
- Avoid reusing a persistent connection (`Connection: close`)
- Add `Pragma: no-cache` and `Cache-Control: no-cache`
- Append a short cache-busting parameter (`_cb=timestamp`) to search and details page requests (unless `DISABLE_CACHE_BUST` is true)

This does NOT anonymize your IP address. For stronger anonymity consider running the container behind:
- A VPN egress
- A rotating proxy provider
- Tor (with appropriate legal/ethical considerations and respecting site ToS)

DNS Bypass Behavior:

When `ABB_DNS_BYPASS=true`, requests to AudiobookBay mirrors are resolved using `ABB_DNS_SERVERS`
instead of your system/router DNS. This helps bypass local DNS filtering (for example, AdGuard DNS)
for ABB mirror lookups while leaving non-ABB traffic unchanged.


The following optional variables add an additional entry to the navigation bar. This is useful for linking to your audiobook player or another related service:

```
NAV_LINK_NAME=Open Audiobook Player
NAV_LINK_URL=https://audiobooks.yourdomain.com/
```

### Using Docker

1. Use `docker-compose` for quick deployment. Example `docker-compose.yml`:

   ```yaml
   version: '3.8'

   services:
     audiobookbay-downloader:
       image: ghcr.io/jamesry96/audiobookbay-automated:latest
       ports:
         - "5078:5078"
       container_name: audiobookbay-downloader
       volumes:
         - ./config:/config
         - ./downloads:/downloads   # staging folder (INPUT_DIR)
         - ./audiobooks:/audiobooks # final library (LIBRARY_DIR), point Audiobookshelf here
         - ./failed:/failed
         - ./work:/work
       environment:
         - DOWNLOAD_CLIENT=qbittorrent
         - DL_SCHEME=http
         - DL_HOST=192.168.1.123
         - DL_PORT=8080
         - DL_USERNAME=admin
         - DL_PASSWORD=pass
         - DL_CATEGORY=abb-downloader
         - SAVE_PATH_BASE=/downloads
         - ABB_HOSTNAME='audiobookbay.is' #Default
         - NAV_LINK_NAME=Open Audiobook Player #Optional
         - NAV_LINK_URL=https://audiobooks.yourdomain.com/ #Optional
         - INPUT_DIR=/downloads
         - LIBRARY_DIR=/audiobooks
         - FAILED_DIR=/failed
         - WORK_DIR=/work
   ```

2. **Start the Application**:
   ```bash
   docker-compose up -d
   ```

### Running Locally
1. **Install Dependencies**:
   Ensure you have Python installed, then install the required dependencies:
   ```bash
   pip install -r requirements.txt
   
2. Create a .env file in the project directory to configure your application. Below is an  example of the required variables:
    ```
    # Torrent Client Configuration
    DOWNLOAD_CLIENT=transmission # Change to delugeweb, transmission or qbittorrent
    DL_SCHEME=http
    DL_HOST=192.168.1.123
    DL_PORT=8080
    DL_USERNAME=admin
    DL_PASSWORD=pass
    DL_CATEGORY=abb-downloader
    SAVE_PATH_BASE=/downloads

    # Agent (organize/tag/move) settings
    INPUT_DIR=/downloads
    LIBRARY_DIR=/audiobooks
    FAILED_DIR=/failed
    WORK_DIR=/work

    # Real-Debrid optional filtering/tracking
    RD_APP_TAG=abb-automated
    RD_TRACKED_TORRENTS_FILE=/downloads/.abb-rd-tracked-torrents.json
    
    # AudiobookBar Hostname
    ABB_HOSTNAME='audiobookbay.is' #Default
    # ABB_HOSTNAME='audiobookbay.lu' #Alternative

    # Optional Navigation Bar Entry
    NAV_LINK_NAME=Open Audiobook Player
    NAV_LINK_URL=https://audiobooks.yourdomain.com/
    ```

3. Start the app:
   ```bash
   python app.py
   ```

### Prod-Like Dev Container Test (Before Release)

Use this when you want to validate branch changes in Docker before tagging/releasing (for example before `1.0.4`).

1. Ensure your `.env` has your test values (or set `DL_USERNAME` / `DL_PASSWORD` to `/run/secrets/...` paths and place files in `./secrets`).
2. Start the dev container:
  ```bash
  docker compose -f docker-compose.dev.yaml up --build -d
  ```
3. View logs:
  ```bash
  docker logs -f audiobookbay-downloader-dev
  ```
4. Stop when finished:
  ```bash
  docker compose -f docker-compose.dev.yaml down
  ```

---

## Notes
- **This app does NOT download any material**: It simply generates magnet links and sends them to your qBittorrent client for handling.

- **Folder Mapping**: __The `SAVE_PATH_BASE` is based on the perspective of your torrent client__, not this app. This app does not move any files; all file handling and organization are managed by the torrent client. Ensure that the `SAVE_PATH_BASE` in your torrent client aligns with your audiobook library (e.g., for Audiobookshelf). Using a path relative to where this app is running, instead of the torrent client, will cause issues.


---

## Feedback and Contributions
This project is a work in progress, and your feedback is welcome! Feel free to open issues or contribute by submitting pull requests.

---

## Screenshots
### Search Results
![screenshot-2025-01-13-19-59-03](https://github.com/user-attachments/assets/8a30fd4e-a289-49d0-83ab-67a3bcfc9745)

### Download Status
![screenshot-2025-01-13-19-59-25](https://github.com/user-attachments/assets/19cc74de-51fc-422f-9cab-fe69e30c74b9)

---
