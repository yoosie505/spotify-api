from http.server import BaseHTTPRequestHandler
import requests
import base64
import os
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Ambil Environment Variables
        c_id = os.environ.get('CLIENT_ID')
        c_sec = os.environ.get('CLIENT_SECRET')
        r_tok = os.environ.get('REFRESH_TOKEN')

        # Cegah error jika Environment Variable belum disetting di dashboard Vercel
        if not all([c_id, c_sec, r_tok]):
            self.kirim({"title": "Error", "artist": "Env Vars Kosong"})
            return

        # 2. Encode kredensial ke Base64
        auth_str = f"{c_id}:{c_sec}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        
        # 3. URL dinormalkan. 
        # (Server Vercel ada di cloud luar negeri, jadi aman dari blokir/sensor internet lokal)
        u_tok = "https://accounts.spotify.com/api/token"
        u_lagu = "https://api.spotify.com/v1/me/player/currently-playing"

        try:
            # 4. Minta Access Token baru
            res_tok = requests.post(
                u_tok, 
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }, 
                data={
                    "grant_type": "refresh_token", 
                    "refresh_token": r_tok
                }
            )
            
            if res_tok.status_code != 200:
                self.kirim({"title": f"Err Token: {res_tok.status_code}", "artist": "-"})
                return
                
            acc_token = res_tok.json().get('access_token')
            
            # 5. Cek lagu yang sedang diputar
            res_lagu = requests.get(
                u_lagu, 
                headers={"Authorization": f"Bearer {acc_token}"}
            )

            # Jika HTTP 200 (Ada lagu) dan respon tidak kosong
            if res_lagu.status_code == 200 and res_lagu.text:
                d = res_lagu.json()
                if d.get('is_playing') and d.get('item'):
                    # Ambil judul dan artis pertama
                    self.kirim({
                        "title": d['item']['name'], 
                        "artist": d['item']['artists'][0]['name']
                    })
                    return
            
            # Jika HTTP 204 (Tidak ada lagu/Spotify sedang dijeda)
            # Debugging error
            self.kirim({
                "title": f"Status: {res_lagu.status_code}", 
                "artist": res_lagu.text if res_lagu.text else "Kosong"
            })
            
        except Exception as e:
            self.kirim({"title": "Error Script", "artist": str(e)})

    def kirim(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        # Wajib pakai .encode('utf-8') agar tidak error jika ada lagu berhuruf Jepang/Korea/Emoji
        self.wfile.write(json.dumps(data).encode('utf-8'))
