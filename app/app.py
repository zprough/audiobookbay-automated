import os, re, requests
from flask import Flask, request, render_template, jsonify
from bs4 import BeautifulSoup
from qbittorrentapi import Client
from transmission_rpc import Client as transmissionrpc
from dotenv import load_dotenv
app = Flask(__name__)

#Load environment variables
load_dotenv()
DOWNLOAD_CLIENT=os.getenv("DOWNLOAD_CLIENT")
DL_HOST = os.getenv("DL_HOST")
DL_PORT = os.getenv("DL_PORT")
DL_USERNAME = os.getenv("DL_USERNAME")
DL_PASSWORD = os.getenv("DL_PASSWORD")
DL_CATEGORY = os.getenv("DL_CATEGORY")
SAVE_PATH_BASE = os.getenv("SAVE_PATH_BASE")

# Custom Nav Link Variables
NAV_LINK_NAME = os.getenv("NAV_LINK_NAME")
NAV_LINK_URL = os.getenv("NAV_LINK_URL")


@app.context_processor
def inject_nav_link():
    return {
        'nav_link_name': os.getenv('NAV_LINK_NAME'),
        'nav_link_url': os.getenv('NAV_LINK_URL')
    }



# Helper function to search AudiobookBay
def search_audiobookbay(query, max_pages=5):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    results = []
    for page in range(1, max_pages + 1):
        url = f"https://audiobookbay.lu/page/{page}/?s={query.replace(' ', '+')}&cat=undefined%2Cundefined"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch page {page}. Status Code: {response.status_code}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        for post in soup.select('.post'):
            try:
                title = post.select_one('.postTitle > h2 > a').text.strip()
                link = f"https://audiobookbay.lu{post.select_one('.postTitle > h2 > a')['href']}"
                cover = post.select_one('img')['src'] if post.select_one('img') else "/static/images/default-cover.jpg"
                results.append({'title': title, 'link': link, 'cover': cover})
            except Exception as e:
                print(f"[ERROR] Skipping post due to error: {e}")
                continue
    return results

# Helper function to extract magnet link from details page
def extract_magnet_link(details_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    response = requests.get(details_url, headers=headers)
    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch details page. Status Code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract Info Hash
    infohash_tag = soup.find('td', text='Info Hash:')
    if not infohash_tag:
        print("[ERROR] Info Hash not found on the page.")
        return None
    infohash = infohash_tag.find_next_sibling('td').text.strip()

    # Extract Trackers
    trackers = [
        tracker.text.strip()
        for tracker in soup.select('td a[href^="udp://"]')
    ]
    if not trackers:
        trackers = [
            "udp://tracker.openbittorrent.com:80",
            "udp://opentor.org:2710",
            "udp://tracker.ccc.de:80",
            "udp://tracker.blackunicorn.xyz:6969",
            "udp://tracker.coppersurfer.tk:6969",
            "udp://tracker.leechers-paradise.org:6969"
        ]

    trackers_query = "&".join(f"tr={tracker}" for tracker in trackers)
    magnet_link = f"magnet:?xt=urn:btih:{infohash}&{trackers_query}"
    print(f"[DEBUG] Generated Magnet Link: {magnet_link}")
    return magnet_link

# Helper function to sanitize titles
def sanitize_title(title):
    return re.sub(r'[<>:"/\\|?*]', '', title).strip()

# Endpoint for search page
@app.route('/', methods=['GET', 'POST'])
def search():
    books = []
    if request.method == 'POST':  # Form submitted
        query = request.form['query']
        #Convert to all lowercase
        query = query.lower()
        if query:  # Only search if the query is not empty
            books = search_audiobookbay(query)
    return render_template('search.html', books=books)


# Endpoint to send magnet link to qBittorrent
@app.route('/send', methods=['POST'])
def send():
    data = request.json
    details_url = data.get('link')
    title = data.get('title')
    if not details_url or not title:
        return jsonify({'message': 'Invalid request'}), 400

    try:
        magnet_link = extract_magnet_link(details_url)
        if not magnet_link:
            return jsonify({'message': 'Failed to extract magnet link'}), 500

        save_path = f"{SAVE_PATH_BASE}/{sanitize_title(title)}"
        
        if DOWNLOAD_CLIENT == 'qbittorrent':
            qb = Client(host=DL_HOST, port=DL_PORT, username=DL_USERNAME, password=DL_PASSWORD)
            qb.auth_log_in()
            qb.torrents_add(urls=magnet_link, save_path=save_path, category=DL_CATEGORY)
        elif DOWNLOAD_CLIENT == 'transmission':
            transmission = transmissionrpc(host=DL_HOST, port=DL_PORT, username=DL_USERNAME, password=DL_PASSWORD)
            transmission.add_torrent(magnet_link, download_dir=save_path)
        else:
            return jsonify({'message': 'Unsupported download client'}), 400

        return jsonify({'message': f'Download added successfully! This may take some time, the download will show in Audiobookshelf when completed.'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500
@app.route('/status')
def status():
    try:
        if DOWNLOAD_CLIENT == 'transmission':
            transmission = transmissionrpc(host=DL_HOST, port=DL_PORT, username=DL_USERNAME, password=DL_PASSWORD)
            torrents = transmission.get_torrents()
            torrent_list = [
                {
                    'name': torrent.name,
                    'progress': round(torrent.progress, 2),
                    'state': torrent.status,
                    'size': f"{torrent.total_size / (1024 * 1024):.2f} MB"
                }
                for torrent in torrents
            ]
            return render_template('status.html', torrents=torrent_list)
        elif DOWNLOAD_CLIENT == 'qbittorrent':
            qb = Client(host=DL_HOST, port=DL_PORT, username=DL_USERNAME, password=DL_PASSWORD)
            qb.auth_log_in()
            torrents = qb.torrents_info(category=DL_CATEGORY)
            torrent_list = [
                {
                    'name': torrent.name,
                    'progress': round(torrent.progress * 100, 2),
                    'state': torrent.state,
                    'size': f"{torrent.total_size / (1024 * 1024):.2f} MB"
                }
                for torrent in torrents
            ]
        else:
            return jsonify({'message': 'Unsupported download client'}), 400
        return render_template('status.html', torrents=torrent_list)
    except Exception as e:
        return jsonify({'message': f"Failed to fetch torrent status: {e}"}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5079)