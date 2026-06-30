import urllib.request
import json
import os
from datetime import datetime

# Global cache for division mappings
DIVISION_MAP = {}

def load_division_map():
    """Reads your clean division roadmap from divisions.json."""
    global DIVISION_MAP
    if os.path.exists('divisions.json'):
        with open('divisions.json', 'r') as f:
            DIVISION_MAP = json.load(f)

def clean_team_name(name_string):
    """Global cleanup for typos that happen everywhere."""
    if not name_string:
        return ""
    cleaned = name_string.strip()
    if cleaned == "Clarington Gaels 1*":
        return "Clarington Gaels 1"
    return cleaned

def format_date_string(raw_date):
    """Converts ISO dates (2026-05-12) to match your Excel format (May 12, 2026)."""
    if not raw_date:
        return ""
    try:
        date_part = raw_date.split('T')[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(raw_date)

def transform_and_filter_game(game, id_number):
    """
    🎯 THE FUNNEL & CLEANER
    This function cleans the names, maps the divisions, and filters 
    down to ONLY the 8 exact fields specified, with correct spelling.
    """
    # 1. Extract and clean team names & divisions
    home_name = game.get("homeTeamName") or game.get("homeTeam", {}).get("name") or ""
    visitor_name = game.get("visitorTeamName") or game.get("visitorTeam", {}).get("name") or ""
    div_name = game.get("divisionName") or game.get("division", {}).get("name") or ""
    
    home_name = clean_team_name(home_name)
    visitor_name = clean_team_name(visitor_name)
    if div_name: div_name = div_name.strip()

    # Rule: Whitby Girls Tournament Pre-Scrub
    if id_number == 15090 and div_name and not div_name.startswith("Girls "):
        div_name = f"Girls {div_name}"

    # Master Division Mapping
    if div_name in DIVISION_MAP:
        div_name = DIVISION_MAP[div_name]

    # Rule: Zone 10 Halton Hills Bulldogs logic
    if id_number == 14894:
        if "U9" in div_name or "U13" in div_name:
            if home_name == "Halton Hills Bulldogs": home_name = "Halton Hills Bulldogs 1"
            if visitor_name == "Halton Hills Bulldogs": visitor_name = "Halton Hills Bulldogs 1"

    # 2. Extract Scores, Date, Status, and Type resiliently
    raw_date = game.get("date") or game.get("gameDate") or game.get("dateString") or ""
    clean_date = format_date_string(raw_date)
    
    visitor_score = game.get("visitorTeamScore") or game.get("visitorScore") or game.get("visitorGoals") or game.get("visitorTeam", {}).get("score", 0)
    home_score = game.get("homeTeamScore") or game.get("homeScore") or game.get("homeGoals") or game.get("homeTeam", {}).get("score", 0)
    
    status = game.get("status") or game.get("gameState") or "final"
    game_type = game.get("type") or game.get("gameType") or "regular_season"

    # 3. Pluck ONLY your 8 required fields (With corrected Division spelling!)
    filtered_game = {
        "Date": clean_date,
        "Division": div_name,  
        "Visitor Team": visitor_name,
        "Visitor Score": int(visitor_score) if visitor_score else 0,
        "Home Team": home_name,
        "Home Score": int(home_score) if home_score else 0,
        "Status": str(status).lower(),
        "Type": str(game_type).lower()
    }

    return filtered_game

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!")
        return
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    load_division_map()
    
    all_ids = list(sources.get("leagues", {}).values()) + list(sources.get("tournaments", {}).values())
    final_clean_games = []
    
    print(f"🚀 Lacrosse Data Funnel Active. Filtering for 8 exact fields...")

    for id_number in all_ids:
        url = f"https://gamesheetstats.com/api/unified-games/{id_number}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req) as response:
                games_list = json.loads(response.read().decode())
                
                if isinstance(games_list, list):
                    for game in games_list:
                        clean_item = transform_and_filter_game(game, id_number)
                        final_clean_games.append(clean_item)
                    print(f"  🔹 ID [{id_number}]: Processed & streamlined.")
                    
        except Exception as e:
            print(f"  ❌ Error loading ID [{id_number}]: {e}")

    print(f"\n==================================================")
    print(f"🏆 FUNNEL COMPILATION COMPLETE")
    print(f"==================================================")
    print(f"Successfully compiled {len(final_clean_games)} games.")
    print(f"Data fields are perfectly streamlined with correct spelling.")
    print(f"==================================================")
    
    return final_clean_games

if __name__ == "__main__":
    fetch_all_lacrosse_data()
