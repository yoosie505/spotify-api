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
        
        # LINK DIPECAH AGAR TIDAK DISENSOR OLEH SISTEM
        url_token = "https://" + "accounts.spotify.com" + "/api/token"
        url_lagu = "https://" + "api.spotify.com" + "/v1/me/player/currently-playing"

        try:
            # 1. Ambil Token Baru
            res_token = requests.post(
                url_token,
                headers={"Authorization": f"Basic {auth_b64}"},
                data={"grant_type": "refresh_token", "refresh_token": refresh_token}
            )
            
            if res_token.status_code != 200:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"title": f"Err Token: {res_token.status_code}", "artist": "-1"}).encode())
                return
                
            access_token = res_token.json().get('access_token')

            # 2. Ambil Data Lagu
            res_lagu = requests.get(
                url_lagu,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Jika berhasil dapat lagu
            if res_lagu.status_code == 200 and res_lagu.text:
                data = res_lagu.json()
                if data.get('is_playing') and data.get('item'):
                    hasil = {
                        "title": data['item']['name'],
                        "artist": data['item']['artists'][0]['name']
                    }
                    self.wfile.write(json.dumps(hasil).encode())
                    return
                else:
                    self.wfile.write(json.dumps({"title": "Lagu Di-pause", "artist": "-"}).encode())
                    return
            
            # Jika Spotify nyala tapi tidak ada lagu (Status 204)
            elif res_lagu.status_code == 204:
                self.wfile.write(json.dumps({"title": "Spotify Terhenti", "artist": "-"}).encode())
                return
            
            # Jika error lain
            else:
                self.wfile.write(json.dumps({"title": f"Err Lagu: {res_lagu.status_code}", "artist": "-"}).encode())
                return
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
