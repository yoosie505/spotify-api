from http.server import BaseHTTPRequestHandler
import requests
import base64
import os
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        client_id = os.environ.get('CLIENT_ID')
        client_secret = os.environ.get('CLIENT_SECRET')
        refresh_token = os.environ.get('REFRESH_TOKEN')

        auth_str = f"{client_id}:{client_secret}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        
        try:
            # 1. Tukar Token ke Server Asli Spotify
            res_token = requests.post(
                "https://accounts.spotify.com/api/token",
                headers={"Authorization": f"Basic {auth_b64}"},
                data={"grant_type": "refresh_token", "refresh_token": refresh_token}
            )
            
            # Cek jika token gagal
            if res_token.status_code != 200:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"title": "Error Token", "artist": "Cek Environment Variables"}).encode())
                return
                
            access_token = res_token.json().get('access_token')

            # 2. Ambil Data Lagu ke Server Asli Spotify
            res_lagu = requests.get(
                "https://api.spotify.com/v1/me/player/currently-playing",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            if res_lagu.status_code == 200 and res_lagu.text:
                data = res_lagu.json()
                if data.get('is_playing') and data.get('item'):
                    hasil = {
                        "title": data['item']['name'],
                        "artist": data['item']['artists'][0]['name']
                    }
                    self.wfile.write(json.dumps(hasil).encode())
                    return

            self.wfile.write(json.dumps({"title": "Spotify Terhenti", "artist": "-"}).encode())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
