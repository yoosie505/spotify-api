import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler

import requests

API_KEY = os.environ.get("LASTFM_API_KEY")
USER = os.environ.get("LASTFM_USER")


def env_int(name, fallback):
    try:
        return int(os.environ.get(name, fallback))
    except (TypeError, ValueError):
        return fallback

LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"
USER_AGENT = "OLED-Music-Display/1.0"

MAX_LYRIC_LINES = 48
MAX_LYRIC_CHARS = 120
FIRST_SEEN_OFFSET_MS = env_int("FIRST_SEEN_OFFSET_MS", 2200)
LYRIC_OFFSET_MS = env_int("LYRIC_OFFSET_MS", 800)

current_track_key = ""
current_track_started_at_ms = 0
lyrics_cache_key = ""
lyrics_cache = {
    "lyrics": [],
    "current_lyric": "",
    "next_lyric": "",
    "duration_ms": 0,
}
metadata_cache = {}


def now_ms():
    return int(time.time() * 1000)


def clean_text(value, fallback=""):
    if value is None:
        return fallback
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def safe_int(value, fallback=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def clamp_progress(progress, duration_ms):
    if duration_ms > 1000:
        return min(max(progress, 0), duration_ms)
    return max(progress, 0)


def trim_lyric(line):
    line = clean_text(line)
    if len(line) <= MAX_LYRIC_CHARS:
        return line
    return line[:MAX_LYRIC_CHARS].rstrip()


def is_now_playing(track):
    return track.get("@attr", {}).get("nowplaying") == "true"


def send_json(handler, payload, status=200):
    handler.send_response(status)
    handler.send_header("Content-type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def stopped_payload(title="Spotify Terhenti"):
    return {
        "title": title,
        "artist": "-",
        "album": "",
        "duration_ms": 0,
        "progress_ms": 0,
        "is_playing": False,
        "current_lyric": "",
        "next_lyric": "",
        "lyrics": [],
    }


def fetch_lastfm_now_playing():
    params = {
        "method": "user.getrecenttracks",
        "user": USER,
        "api_key": API_KEY,
        "format": "json",
        "limit": 1,
    }
    response = requests.get(LASTFM_URL, params=params, timeout=4)
    response.raise_for_status()
    data = response.json()
    tracks = data.get("recenttracks", {}).get("track", [])
    if not tracks:
        return None
    return tracks[0]


def fetch_lastfm_track_info(title, artist):
    cache_key = f"{artist.lower()}::{title.lower()}"
    if cache_key in metadata_cache:
        return metadata_cache[cache_key]

    params = {
        "method": "track.getInfo",
        "api_key": API_KEY,
        "artist": artist,
        "track": title,
        "format": "json",
        "autocorrect": 1,
    }
    response = requests.get(LASTFM_URL, params=params, timeout=4)
    response.raise_for_status()
    track = response.json().get("track", {})
    duration_ms = safe_int(track.get("duration"), 0)
    album = clean_text(track.get("album", {}).get("title", ""))
    metadata_cache[cache_key] = (duration_ms, album)
    return metadata_cache[cache_key]


def parse_lrc(synced_lyrics):
    lines = []
    if not synced_lyrics:
        return lines

    for raw_line in synced_lyrics.splitlines():
        match = re.match(r"^\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)$", raw_line)
        if not match:
            continue

        minute = safe_int(match.group(1))
        second = safe_int(match.group(2))
        fraction = match.group(3) or "0"
        millis = safe_int(fraction.ljust(3, "0")[:3])
        words = trim_lyric(match.group(4))

        if not words:
            continue

        lines.append({
            "time_ms": ((minute * 60) + second) * 1000 + millis,
            "words": words,
        })

        if len(lines) >= MAX_LYRIC_LINES:
            break

    return lines


def lyric_at_progress(lyrics, progress_ms):
    current = ""
    next_line = ""

    for index, line in enumerate(lyrics):
        if line["time_ms"] <= progress_ms:
            current = line["words"]
            if index + 1 < len(lyrics):
                next_line = lyrics[index + 1]["words"]
        else:
            if not next_line:
                next_line = line["words"]
            break

    return current, next_line


def fetch_lrclib_lyrics(title, artist, duration_ms):
    global lyrics_cache_key, lyrics_cache

    cache_key = f"{artist.lower()}::{title.lower()}::{duration_ms // 1000}"
    if cache_key == lyrics_cache_key:
        return lyrics_cache

    result = {
        "lyrics": [],
        "current_lyric": "",
        "next_lyric": "",
        "duration_ms": 0,
        "album": "",
    }

    try:
        response = requests.get(
            LRCLIB_SEARCH_URL,
            params={"track_name": title, "artist_name": artist},
            headers={"User-Agent": USER_AGENT},
            timeout=4,
        )
        response.raise_for_status()
        candidates = response.json()
    except Exception:
        lyrics_cache_key = cache_key
        lyrics_cache = result
        return result

    if not candidates:
        lyrics_cache_key = cache_key
        lyrics_cache = result
        return result

    duration_sec = duration_ms / 1000 if duration_ms else 0

    def score(item):
        title_score = 0 if clean_text(item.get("trackName")).lower() == title.lower() else 10
        artist_score = 0 if artist.lower() in clean_text(item.get("artistName")).lower() else 10
        item_duration = safe_int(item.get("duration"), 0)
        duration_score = abs(item_duration - duration_sec) if duration_sec else 0
        return title_score + artist_score + duration_score

    best = sorted(candidates, key=score)[0]
    synced = best.get("syncedLyrics") or ""
    plain = best.get("plainLyrics") or ""
    lyrics = parse_lrc(synced)

    if lyrics:
        result["lyrics"] = lyrics
    elif plain:
        plain_lines = [trim_lyric(line) for line in plain.splitlines() if trim_lyric(line)]
        result["current_lyric"] = plain_lines[0] if len(plain_lines) > 0 else ""
        result["next_lyric"] = plain_lines[1] if len(plain_lines) > 1 else ""

    result["duration_ms"] = safe_int(best.get("duration"), 0) * 1000
    result["album"] = clean_text(best.get("albumName", ""))
    lyrics_cache_key = cache_key
    lyrics_cache = result
    return result


def estimate_progress_ms(track_key, duration_ms):
    global current_track_key, current_track_started_at_ms

    current_time = now_ms()
    if track_key != current_track_key or current_track_started_at_ms == 0:
        current_track_key = track_key
        current_track_started_at_ms = current_time - FIRST_SEEN_OFFSET_MS

    progress = current_time - current_track_started_at_ms
    return clamp_progress(progress, duration_ms)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not API_KEY or not USER:
            send_json(self, stopped_payload("API Env Kosong"), status=500)
            return

        try:
            track = fetch_lastfm_now_playing()
            if not track or not is_now_playing(track):
                send_json(self, stopped_payload())
                return

            title = clean_text(track.get("name"), "Unknown Track")
            artist = clean_text(track.get("artist", {}).get("#text"), "Unknown Artist")
            track_key = f"{artist.lower()}::{title.lower()}"

            lyrics_data = fetch_lrclib_lyrics(title, artist, 0)
            duration_ms = lyrics_data["duration_ms"]
            album = lyrics_data["album"]
            if duration_ms < 1000:
                duration_ms, album = fetch_lastfm_track_info(title, artist)
                if duration_ms >= 1000:
                    lyrics_data = fetch_lrclib_lyrics(title, artist, duration_ms)
                    if not album:
                        album = lyrics_data["album"]

            progress_ms = estimate_progress_ms(track_key, duration_ms)
            lyric_progress_ms = clamp_progress(progress_ms + LYRIC_OFFSET_MS, duration_ms)
            current_lyric, next_lyric = lyric_at_progress(lyrics_data["lyrics"], lyric_progress_ms)
            if not current_lyric:
                current_lyric = lyrics_data["current_lyric"]
            if not next_lyric:
                next_lyric = lyrics_data["next_lyric"]

            send_json(self, {
                "title": title,
                "artist": artist,
                "album": album,
                "duration_ms": duration_ms,
                "progress_ms": progress_ms,
                "lyric_progress_ms": lyric_progress_ms,
                "lyric_offset_ms": LYRIC_OFFSET_MS,
                "is_playing": True,
                "current_lyric": current_lyric,
                "next_lyric": next_lyric,
                "lyrics": lyrics_data["lyrics"],
            })
        except Exception as error:
            payload = stopped_payload("API Last.fm Error")
            payload["error"] = str(error)
            send_json(self, payload, status=500)
