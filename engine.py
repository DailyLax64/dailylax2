import urllib.request
import json
import os

# Global cache for division mappings
DIVISION_MAP = {}

def load_division_map():
    """Reads your clean division roadmap from divisions.json."""
    global DIVISION_MAP
    if os.path.exists('divisions.json'):
        with open('divisions.json', 'r') as f:
            DIVISION_MAP = json.load(f)
    else:
        print("⚠️ Warning: divisions.json mapping file not found. Skipping auto-mapping.")

def clean_team_name(name_string):
    """Global cleanup for typos that happen everywhere."""
    if not name_string:
        return ""
    cleaned = name_string.strip()
    
    # Rule 1: Fix the Clarington Gaels asterisk typo
    if cleaned == "Clarington Gaels 1*":
        return "Clarington Gaels 1"
        
    return cleaned

def transform_game_data(game, id_number):
    """
    🧠 THE CONTEXT & DIVISION CLEANER
    This function processes every game, maps out the messy divisions, 
    and applies regional formatting rule corrections.
    """
    # 1. Pull down raw elements safely
    home_name = game.get("homeTeamName") or game.get("homeTeam", {}).get("name") or ""
    visitor_name = game.get("visitorTeamName") or game.get("visitorTeam", {}).get("name") or ""
    div_name = game.get("divisionName") or game.get("division", {}).get("name") or ""
    
    # Run structural cleanup on strings
    home_name = clean_team_name(home_name)
    visitor_name = clean_team_name(visitor_name)
    if div_name: div_name = div_name.strip()

    # 2. Rule: Whitby Girls Tournament (ID 15090) Pre-Scrub
    # If it's the Whitby girls tournament, ensure it has "Girls " attached before searching maps
    if id_number == 15090 and div_name and not div_name.startswith("Girls "):
        div_name = f"Girls {div_name}"

    # 3. Master Division Mapping Check (replaces messy tags with clean ones)
    if div_name in DIVISION_MAP:
        div_name = DIVISION_MAP[div_name]

    # 4. Rule: Zone 10 (ID 14894) Halton Hills Bulldogs logic
    if id_number == 14894:
        if "U9" in div_name or "U13" in div_name:
            if home_name == "Halton Hills Bulldogs":
                home_name = "Halton Hills Bulldogs 1"
            if visitor_name == "Halton Hills Bulldogs":
                visitor_name = "Halton Hills Bulldogs 1"

    # 5. Pack cleaned parameters back into our master data pipeline package
    if "homeTeamName" in game: game["homeTeamName"] = home_name
    if "homeTeam" in game and isinstance(game["homeTeam"], dict): game["homeTeam"]["name"] = home_name
        
    if "visitorTeamName" in game: game["visitorTeamName"] = visitor_name
    if "visitorTeam" in game and isinstance(game["visitorTeam"], dict): game["visitorTeam"]["name"] = visitor_name
    
    if "divisionName" in game: game["divisionName"] = div_name
    if "division" in game and isinstance(game["division"], dict): game["division"]["name"] = div_name

    return game

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!")
        return
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    # Fire up your layout map arrays
    load_division_map()
    
    league_ids = list(sources.get("leagues", {}).values())
    tournament_ids = list(sources.get("tournaments", {}).values())
    all_ids = league_ids + tournament_ids
    
    all_raw_games = []
    
    print(f"🚀 Lacrosse Data Pipeline Active.")
    print(f"📡 Processing {len(all_ids)} total GameSheet data streams...\n")

    for id_number in all_ids:
        url = f"https://gamesheetstats.com/api/unified-games/{id_number}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req) as response:
                games_list = json.loads(response.read().decode())
                
                if isinstance(games_list, list):
                    cleaned_games = [transform_game_data(game, id_number) for game in games_list]
                    all_raw_games.extend(cleaned_games)
                    print(f"  🔹 ID [{id_number}]: Connected and mapped.")
                else:
                    print(f"  ⚠️ ID [{id_number}]: Unexpected layout format.")
                    
        except Exception as e:
            print(f"  ❌ Error loading ID [{id_number}]: {e}")

    print(f"\n==================================================")
    print(f"🏆 PIPELINE DATA AGGREGATION & CLEANING COMPLETE")
    print(f"==================================================")
    print(f"Successfully processed {len(all_raw_games)} clean games into memory.")
    print(f"All divisions consolidated safely using master dictionary map rules.")
    print(f"==================================================")

if __name__ == "__main__":
    fetch_all_lacrosse_data()
