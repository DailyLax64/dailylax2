import urllib.request
import json
import os
from datetime import datetime

# Global cache for division mappings
DIVISION_MAP = {}

def load_division_map():
    if os.path.exists('divisions.json'):
        with open('divisions.json', 'r') as f:
            DIVISION_MAP = json.load(f)

def clean_team_name(name_string):
    if not name_string: return ""
    cleaned = name_string.strip()
    if cleaned == "Clarington Gaels 1*": return "Clarington Gaels 1"
    return cleaned

def format_date_string(raw_date):
    if not raw_date: return ""
    try:
        date_part = raw_date.split('T')[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(raw_date)

def transform_and_filter_game(game, id_number):
    # This function is trying to guess the keys. Let's see what keys actually exist!
    home_name = game.get("homeTeamName") or game.get("homeTeam", {}).get("name") or ""
    visitor_name = game.get("visitorTeamName") or game.get("visitorTeam", {}).get("name") or ""
    div_name = game.get("divisionName") or game.get("division", {}).get("name") or ""
    
    home_name = clean_team_name(home_name)
    visitor_name = clean_team_name(visitor_name)
    if div_name: div_name = div_name.strip()

    if id_number == 15090 and div_name and not div_name.startswith("Girls "):
        div_name = f"Girls {div_name}"

    if div_name in DIVISION_MAP:
        div_name = DIVISION_MAP[div_name]

    if id_number == 14894:
        if "U9" in div_name or "U13" in div_name:
            if home_name == "Halton Hills Bulldogs": home_name = "Halton Hills Bulldogs 1"
            if visitor_name == "Halton Hills Bulldogs": visitor_name = "Halton Hills Bulldogs 1"

    raw_date = game.get("date") or game.get("gameDate") or game.get("dateString") or ""
    clean_date = format_date_string(raw_date)
    
    raw_status = game.get("status") or game.get("gameState") or "final"
    visitor_score = game.get("visitorTeamScore") or game.get("visitorScore") or game.get("visitorGoals") or game.get("visitorTeam", {}).get("score", 0)
    home_score = game.get("homeTeamScore") or game.get("homeScore") or game.get("homeGoals") or game.get("homeTeam", {}).get("score", 0)
    
    game_type = game.get("type") or game.get("gameType") or "regular_season"

    return {
        "Date": clean_date,
        "Division": div_name,  
        "Visitor Team": visitor_name,
        "Visitor Score": int(visitor_score) if visitor_score else 0,
        "Home Team": home_name,
        "Home Score": int(home_score) if home_score else 0,
        "Status": str(raw_status).strip().lower(),
        "Type": str(game_type).lower()
    }

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!", flush=True)
        return
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    load_division_map()
    
    all_ids = []
    if isinstance(sources, dict):
        if "leagues" in sources or "tournaments" in sources:
            all_ids = list(sources.get("leagues", {}).values()) + list(sources.get("tournaments", {}).values())
        else:
            all_ids = list(sources.values())

    final_clean_games = []
    has_dumped_diagnostics = False

    for id_number in all_ids:
        url = f"https://gamesheetstats.com/api/unified-games/{id_number}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req) as response:
                games_list = json.loads(response.read().decode())
                
                target_list = []
                if isinstance(games_list, list):
                    target_list = games_list
                elif isinstance(games_list, dict):
                    target_list = games_list.get("games") or games_list.get("data") or games_list.get("unifiedGames") or []
                
                # 🔬 CRITICAL DIAGNOSTIC DROP
                # Let's inspect the very first game object ever found across all 5,066 items!
                if target_list and not has_dumped_diagnostics:
                    print("\n" + "="*80, flush=True)
                    print("🔬 RAW GAMESHEET API OBJECT INSPECTOR", flush=True)
                    print("="*80, flush=True)
                    print("Here are all available top-level keys in GameSheet's raw data stream:", flush=True)
                    print(list(target_list[0].keys()), flush=True)
                    print("\nHere is a full sample text printout of a raw match card object:", flush=True)
                    print(json.dumps(target_list[0], indent=2), flush=True)
                    print("="*80 + "\n", flush=True)
                    has_dumped_diagnostics = True
                
                for game in target_list:
                    clean_item = transform_and_filter_game(game, id_number)
                    final_clean_games.append(clean_item)
        except Exception:
            pass

    print(f"✅ Downloaded {len(final_clean_games)} total match cards.", flush=True)

if __name__ == "__main__":
    fetch_all_lacrosse_data()
