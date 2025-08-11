# Project Structure Documentation

## New Organized Folder Structure (Option 3: Simple Organized)

The project has been refactored to use a clean, organized folder structure that separates concerns and improves maintainability.

### Structure Overview

```
app/
├── __init__.py              # Main app package init
├── app.py                   # Flask application entry point (routes only)
├── requirements.txt         # Python dependencies
├── api/                     # API-related modules
│   ├── __init__.py         # API package exports
│   └── torznab_api.py      # Torznab API implementation
├── clients/                 # Download client modules
│   ├── __init__.py         # Clients package exports
│   └── download_client.py  # Download client management
├── scraper/                 # Web scraping modules
│   ├── __init__.py         # Scraper package exports
│   └── audiobookbay_scraper.py  # AudiobookBay scraping logic
├── static/                  # Static web assets
│   ├── css/                # CSS stylesheets
│   └── images/             # Images and media
└── templates/              # HTML templates
    ├── base.html
    ├── search.html
    └── status.html
```

### Module Organization

#### 1. Core Application (`app.py`)
- **Purpose**: Flask application entry point and route definitions
- **Responsibilities**: 
  - Web routes and request handling
  - Template rendering
  - Application configuration
- **Clean imports**: Uses organized package imports

#### 2. API Package (`api/`)
- **Purpose**: External API integrations and endpoints
- **Contents**:
  - `torznab_api.py`: Torznab API for Lazylibrarian integration
- **Features**: 
  - Blueprint-based organization
  - XML response generation
  - API key authentication

#### 3. Clients Package (`clients/`)
- **Purpose**: Download client integrations
- **Contents**:
  - `download_client.py`: Unified download client management
- **Features**:
  - Factory pattern for client selection
  - Support for qBittorrent, Transmission, Deluge
  - Error handling and logging

#### 4. Scraper Package (`scraper/`)
- **Purpose**: Web scraping and data extraction
- **Contents**:
  - `audiobookbay_scraper.py`: AudiobookBay scraping logic
- **Features**:
  - Search functionality
  - Magnet link extraction
  - Title sanitization and utilities

### Benefits of This Structure

1. **Separation of Concerns**: Each package handles a specific responsibility
2. **Maintainability**: Easy to locate and modify specific functionality
3. **Testability**: Modular structure enables better unit testing
4. **Scalability**: Easy to add new APIs, clients, or scrapers
5. **Clean Imports**: Organized package imports improve code readability

### Import Strategy

The application uses absolute imports within the app package:
- `from api import torznab_bp`
- `from scraper import search_audiobookbay, extract_magnet_link, get_scraper_stats`
- `from clients import add_torrent, get_torrents, get_client_info, DownloadClientError`

### Development Environment

The development script (`scripts/dev-local.sh`) has been updated to:
- Automatically detect and use the virtual environment
- Set proper environment variables
- Start the Flask server on port 5079 with debug mode

### Next Steps

With this organized structure in place, future enhancements become much easier:
- Adding new scraper modules for other sites
- Implementing additional download clients
- Creating new API endpoints
- Adding comprehensive test suites
- Implementing proper logging configuration

### Environment Variable Handling

The application properly handles environment variables in both local development and containerized environments:

#### **Local Development**
- Uses `.env` file in project root for configuration
- `load_dotenv(override=False)` ensures existing environment variables take precedence
- Settings page writes changes to project `.env` file

#### **Container/Docker Mode**
- Docker Compose environment variables take highest precedence
- Settings page detects container mode (`/.dockerenv` file or `CONTAINER=docker`)
- Attempts to write settings to `/config/.env` (mounted volume)
- Falls back to app directory if no writable config volume available
- Shows warnings about Docker Compose overrides and persistence

#### **Environment Variable Precedence**
1. **Docker Compose environment variables** (highest priority)
2. **System environment variables**
3. **`.env` file settings** (lowest priority)

This ensures that Docker deployments work correctly while maintaining flexibility for local development.
