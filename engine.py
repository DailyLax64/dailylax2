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
    
    # Track raw values directly to spot API mismatches
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

def run_pipeline_auditor(games_list):
    """
    🔬 THE PIPELINE AUDITOR
    Inspects your 5,065 compiled items to tell us exactly why 
    the ranking filter dropped them.
    """
    if not games_list:
        print("❌ Auditor Error: The dataset passed in is completely empty.")
        return

    print("\n" + "="*75)
    print("🔬 PIPELINE AUDITOR REPORT")
    print("="*75)
    
    # 1. Print exactly what the first item looks like inside memory
    print("🎯 SAMPLE GAME OBJECT STRIPPED BY PYTHON:")
    print(json.dumps(games_list[0], indent=2))
    print("-"*75)

    # 2. Audit unique values found in the Status column
    status_values = {}
    division_values = set()
    empty_division_count = 0
    
    for g in games_list:
        stat = g["Status"]
        div = g["Division"]
        status_values[stat] = status_values.get(stat, 0) + 1
        if div:
            division_values.add(div)
        else:
            empty_division_count += 1

    print("🚦 ALL UNIQUE STATUS STRINGS FOUND IN DATA:")
    for stat, count in status_values.items():
        print(f"  ▪️ '{stat}' : found in {count} games")
        
    print(f"\n📦 DIVISION SUMMARY:")
    print(f"  ▪️ Total Unique Divisions Found: {len(division_values)}")
    print(f"  ▪️ Games with BLANK/EMPTY Divisions: {empty_division_count}")
    print("="*75 + "\n")

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!")
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

    for id_number in all_ids:
        url = f"https://gamesheetstats.com/api/unified-games/{id_number}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req) as response:
                games_list = json.loads(response.read().decode())
                target_list = games_list if isinstance(games_list, list) else games_list.get("games", [])
                for game in target_list:
                    clean_item = transform_and_filter_game(game, id_number)
                    final_clean_games.append(clean_item)
        except Exception:
            pass

    # Run our diagnostic check to look inside memory
    run_pipeline_auditor(final_clean_games)

if __name__ == "__main__":
    fetch_all_lacrosse_data()
