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
    """Cleans names, maps divisions, and slices data down to 8 fields."""
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
    
    visitor_score = game.get("visitorTeamScore") or game.get("visitorScore") or game.get("visitorGoals") or game.get("visitorTeam", {}).get("score", 0)
    home_score = game.get("homeTeamScore") or game.get("homeScore") or game.get("homeGoals") or game.get("homeTeam", {}).get("score", 0)
    
    status = game.get("status") or game.get("gameState") or "final"
    game_type = game.get("type") or game.get("gameType") or "regular_season"

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

def print_audit_report(games):
    """
    📊 THE VISUAL AUDIT PANEL
    This takes the games currently in memory and builds a clean 
    dashboard directly in your terminal logs for you to review.
    """
    if not games:
        print("⚠️ No games found to report.")
        return

    # 1. Count games per division to spot anomallies
    division_counts = {}
    for g in games:
        div = g["Division"] or "Unknown"
        division_counts[div] = division_counts.get(div, 0) + 1

    print("\n" + "="*50)
    print("📋 DIVISION GAME COUNTS (AUDIT CHECKLIST)")
    print("="*50)
    for div, count in sorted(division_counts.items()):
        print(f" 📦 {div.ljust(18)} : {count} games processed")
    
    # 2. Print a sample table of scores to verify names and numbers
    print("\n" + "="*85)
    print("👀 LIVE DATA PREVIEW (SAMPLE OF FIRST 10 GAMES COMPILED)")
    print("="*85)
    print(f"{'Date'.ljust(14)} | {'Division'.ljust(10)} | {'Matchup & Final Score'.ljust(45)} | {'Type'}")
    print("-"*85)
    
    # Show up to the first 10 games as a sample snapshot
    for g in games[:10]:
        matchup = f"{g['Home Team']} ({g['Home Score']}) vs {g['Visitor Team']} ({g['Visitor Score']})"
        print(f"{g['Date'].ljust(14)} | {g['Division'].ljust(10)} | {matchup.ljust(45)} | {g['Type']}")
    print("="*85 + "\n")

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!")
        return []
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    load_division_map()
    all_ids = list(sources.get("leagues", {}).values()) + list(sources.get("tournaments", {}).values())
    final_clean_games = []
    
    print(f"🚀 Lacrosse Data Funnel Active. Connecting to streams...")

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
        except Exception:
            pass # Keep rolling quietly during aggregation

    # Run our brand new audit report!
    print_audit_report(final_clean_games)
    return final_clean_games

if __name__ == "__main__":
    fetch_all_lacrosse_data()
