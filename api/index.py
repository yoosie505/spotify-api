import os
import json
import requests
from http.server import BaseHTTPRequestHandler

# Ambil rahasia dari Environment Variables Vercel
API_KEY = os.environ.get("LASTFM_API_KEY")
USER = os.environ.get("LASTFM_USER")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()

        url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={USER}&api_key={API_KEY}&format=json&limit=1"

        try:
            res = requests.get(url)
            data = res.json()
            track = data['recenttracks']['track'][0]

            # Cek apakah lagu benar-benar SEDANG diputar sekarang (ada tulisan nowplaying)
            is_playing = False
            if '@attr' in track and track['@attr'].get('nowplaying') == 'true':
                is_playing = True

            if is_playing:
                title = track['name']
                artist = track['artist']['#text']
                
                # Format JSON dikirim lengkap biar C++ kamu aman!
                hasil_json = {
                    "title": title,
                    "artist": artist,
                    "duration_ms": 0,
                    "progress_ms": 0,
                    "is_playing": True,
                    "current_lyric": "",
                    "next_lyric": ""
                }
                self.wfile.write(json.dumps(hasil_json).encode())
            else:
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
                
        except Exception as e:
            error_json = {
                "title": "API Last.fm Error",
                "artist": "-",
                "is_playing": False
            }
            self.wfile.write(json.dumps(error_json).encode())
