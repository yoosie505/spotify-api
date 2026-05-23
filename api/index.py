import os
import json
import requests
import re
from http.server import BaseHTTPRequestHandler

# Ambil data rahasia dari Environment Variables Vercel
CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN")

def get_access_token():
    url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    try:
        res = requests.post(url, data=data)
        return res.json().get("access_token")
    except:
        return None

def get_current_lyrics(artist_name, track_name, progress_ms):
    url = f"https://lrclib.net/api/get?artist_name={artist_name}&track_name={track_name}"
    try:
        req = requests.get(url, timeout=3)
        data = req.json()
        if 'syncedLyrics' not in data or not data['syncedLyrics']:
            return "Lirik tidak tersedia", ""
            
        lrc_text = data['syncedLyrics']
        pattern = re.compile(r'\[(\d{2}):(\d{2}\.\d{2})\](.*)')
        lines = lrc_text.split('\n')
        
        lyrics_data = []
        for line in lines:
            match = pattern.match(line)
            if match:
                mins = int(match.group(1))
                secs = float(match.group(2))
                text = match.group(3).strip()
                time_ms = int((mins * 60 + secs) * 1000)
                if text:
                    lyrics_data.append({'time': time_ms, 'text': text})
        
        current_lyric = "..."
        next_lyric = "..."
        for i in range(len(lyrics_data)):
            if progress_ms >= lyrics_data[i]['time']:
                current_lyric = lyrics_data[i]['text']
                if i + 1 < len(lyrics_data):
                    next_lyric = lyrics_data[i+1]['text']
                else:
                    next_lyric = ""
            else:
                break
        return current_lyric, next_lyric
    except:
        return "Gagal memuat lirik", ""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') # Biar bisa ditembak ESP32
        self.end_headers()

        access_token = get_access_token()
        if not access_token:
            self.wfile.write(json.dumps({"title": "Spotify Terhenti", "artist": "-", "is_playing": False}).encode())
            return

        # Tembak Spotify API Currently Playing
        headers = {"Authorization": f"Bearer {access_token}"}
        spotify_res = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)

        if spotify_res.status_code == 200:
            spotify_data = spotify_res.json()
            if spotify_data.get('is_playing'):
                title = spotify_data['item']['name']
                artist = spotify_data['item']['artists'][0]['name']
                duration_ms = spotify_data['item']['duration_ms']
                progress_ms = spotify_data['progress_ms']
                is_playing = spotify_data['is_playing']
                
                # Ambil lirik berdasarkan detik lagu
                current_lyric, next_lyric = get_current_lyrics(artist, title, progress_ms)
                
                hasil_json = {
                    "title": title,
                    "artist": artist,
                    "duration_ms": duration_ms,
                    "progress_ms": progress_ms,
                    "is_playing": is_playing,
                    "current_lyric": current_lyric,
                    "next_lyric": next_lyric
                }
                self.wfile.write(json.dumps(hasil_json).encode())
                return

        # Jika sedang di-pause atau tidak ada lagu berputar
        hasil_pasif = {
            "title": "Spotify Terhenti",
            "artist": "-",
            "duration_ms": 0,
            "progress_ms": 0,
            "is_playing": False,
            "current_lyric": "",
            "next_lyric": ""
        }
        self.wfile.write(json.dumps(hasil_pasif).encode())
