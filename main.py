import os
import sys
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from nba_api.stats.endpoints import LeagueStandings
import time
from team_names import TEAM_NAME_TO_FULL

# === Determine base directory of exe/script ===
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

APPDATA = os.getenv("APPDATA")
DATA_DIR = os.path.join(APPDATA, "NBAStandingsFetcher")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "standings.json")

# === Load configuration ===
with open(CONFIG_FILE) as f:
    config = json.load(f)

PC_IP = config.get("pc_ip", "")
SERVER_PORT = config.get("server_port", 8000)
UPDATE_INTERVAL = config.get("update_interval", 600)

def fetch_standings():
    """Fetch NBA standings with full team names."""
    print("Fetching NBA standings...")
    try:
        standings_resp = LeagueStandings()
        standings_data = standings_resp.get_data_frames()[0]

        result = {"East": [], "West": []}
        for _, row in standings_data.iterrows():
            conf = row['Conference']
            if conf in result:
                name = row['TeamName']
                full_name = TEAM_NAME_TO_FULL.get(name, row['TeamName'])
                games_behind = float(row['ConferenceGamesBack'])
                result[conf].append({
                    "team": full_name,
                    "games_behind": games_behind,
                    "wins": int(row['WINS']),
                    "losses": int(row['LOSSES'])
                })

        # Sort by wins descending
        for conf in result:
            result[conf].sort(key=lambda x: x["wins"], reverse=True)

        return result
    except Exception as e:
        print("Error fetching NBA data:", e)
        return None

def save_json(data):
    """Save simplified standings as JSON."""
    try:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Standings saved to {OUTPUT_FILE}")
    except Exception as e:
        print("Failed to save standings:", e)

def start_http_server():
    """Start HTTP server in the exe folder."""
    print(f"Starting HTTP server on port {SERVER_PORT}...")
    os.chdir(BASE_DIR)  # serve files from the exe folder
    server_address = ("", SERVER_PORT)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"HTTP server ready. ESP32 can fetch http://{PC_IP}:{SERVER_PORT}/{os.path.basename(OUTPUT_FILE)}")
    httpd.serve_forever()

def auto_update_standings():
    """Continuously update standings every UPDATE_INTERVAL seconds."""
    while True:
        data = fetch_standings()
        if data:
            save_json(data)
        else:
            print("Failed to fetch standings, retrying later...")
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    # Start auto-update thread
    update_thread = threading.Thread(target=auto_update_standings, daemon=True)
    update_thread.start()

    # Start HTTP server
    start_http_server()
