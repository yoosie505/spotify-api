from http.server import BaseHTTPRequestHandler
import requests
import os
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        api_key = os.environ.get('LASTFM_API_KEY')
        username = os.environ.get('LASTFM_USER')

        if not api_key or not username:
            self.kirim({"title": "Error", "artist": "Env Vars Kosong", "duration_ms": 0, "progress_ms": 0, "is_playing": False})
            return

        url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key={api_key}&format=json&limit=1"

        try:
            res = requests.get(url)
            if res.status_code == 200 and res.text:
                data = res.json()
                if "recenttracks" in data and "track" in data["recenttracks"]:
                    tracks = data["recenttracks"]["track"]
                    
                    if len(tracks) > 0:
                        track = tracks[0] 
                        
                        # Cek lagu SEDANG diputar
                        if "@attr" in track and track["@attr"].get("nowplaying") == "true":
                            self.kirim({
                                "title": track["name"], 
                                "artist": track["artist"]["#text"],
                                "duration_ms": 1, # Syarat agar icon Play muncul di OLED
                                "progress_ms": 0,
                                "is_playing": True
                            })
                            return
            
            # Jika tidak ada lagu
            self.kirim({"title": "Spotify Terhenti", "artist": "-", "duration_ms": 0, "progress_ms": 0, "is_playing": False})

        except Exception as e:
            self.kirim({"title": "Error Script", "artist": str(e), "duration_ms": 0, "progress_ms": 0, "is_playing": False})

    def kirim(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
