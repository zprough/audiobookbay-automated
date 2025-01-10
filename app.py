import re
from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup
from qbittorrentapi import Client

app = Flask(__name__)

# qBittorrent Configuration
QB_HOST = "192.168.12.153"
QB_PORT = 8080
QB_USERNAME = "admin" #Change to your qBittorrent username
QB_PASSWORD = "CHANGEME" #Change to your qBittorrent password
QB_CATEGORY = "abb-downloader" 
SAVE_PATH_BASE = "/audiobooks" #Change to where you want your audiobooks to be saved relative to the qbittorent client

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
                cover = post.select_one('img')['src'] if post.select_one('img') else "/images/default-cover.jpg"
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
def send_to_qb():
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
        qb = Client(host=QB_HOST, port=QB_PORT, username=QB_USERNAME, password=QB_PASSWORD)
        qb.auth_log_in()
        qb.torrents_add(urls=magnet_link, save_path=save_path, category=QB_CATEGORY)
        return jsonify({'message': f'Download added successfully! This may take some time, the download will show in Audiobookshelf when completed.'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5078)