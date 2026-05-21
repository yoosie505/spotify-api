from http.server import BaseHTTPRequestHandler
import requests
import base64
import os
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Ambil kunci dari Environment Variables Vercel
        client_id = os.environ.get('CLIENT_ID')
        client_secret = os.environ.get('CLIENT_SECRET')
        refresh_token = os.environ.get('REFRESH_TOKEN')

        # 1. Tukar Refresh Token dengan Access Token baru
        auth_str = f"{client_id}:{client_secret}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        
        res_token = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth_b64}"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token}
        )
        access_token = res_token.json().get('access_token')

        # 2. Ambil status lagu Spotify saat ini
        res_lagu = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # 3. Format dan kirim data ke ESP32
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if res_lagu.status_code == 200 and res_lagu.text:
            data = res_lagu.json()
            if data.get('is_playing'):
                hasil = {
                    "title": data['item']['name'],
                    "artist": data['item']['artists'][0]['name']
                }
                self.wfile.write(json.dumps(hasil).encode())
                return

        # Jika sedang tidak memutar lagu
        self.wfile.write(json.dumps({"title": "Spotify Terhenti", "artist": "-"}).encode())
        return
