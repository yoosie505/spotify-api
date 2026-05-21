from http.server import BaseHTTPRequestHandler
import requests
import os
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Ambil API Key dan Username dari Vercel
        api_key = os.environ.get('2382657f68d0eadf265a4c302481cd9d')
        username = os.environ.get('Musanis')

        # Cegah error jika Environment Variable belum diisi
        if not api_key or not username:
            self.kirim({"title": "Error", "artist": "Env Vars Kosong"})
            return

        # 2. URL Endpoint Last.fm API
        url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key={api_key}&format=json&limit=1"

        try:
            res = requests.get(url)
            
            if res.status_code == 200 and res.text:
                data = res.json()
                
                # 3. Cek struktur data dari Last.fm
                if "recenttracks" in data and "track" in data["recenttracks"]:
                    tracks = data["recenttracks"]["track"]
                    
                    if len(tracks) > 0:
                        track = tracks[0] # Ambil lagu urutan pertama
                        
                        # 4. Cek apakah lagu tersebut SEDANG diputar detik ini juga
                        # Last.fm menandainya dengan atribut @attr -> nowplaying: "true"
                        if "@attr" in track and track["@attr"].get("nowplaying") == "true":
                            title = track["name"]
                            artist = track["artist"]["#text"]
                            
                            self.kirim({"title": title, "artist": artist})
                            return
            
            # Jika tidak ada lagu yang diputar saat ini
            self.kirim({"title": "Spotify Terhenti", "artist": "-"})

        except Exception as e:
            self.kirim({"title": "Error Script", "artist": str(e)})

    def kirim(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
