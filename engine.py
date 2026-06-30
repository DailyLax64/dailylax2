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
    """Converts ISO dates to match your standard date format."""
    if not raw_date:
        return ""
    try:
        date_part = raw_date.split('T')[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(raw_date)

def transform_and_filter_game(game, id_number):
    """Cleans data and strips individual matches to your 8 required fields."""
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

    return {
        "Date": clean_date,
        "Division": div_name,  
        "Visitor Team": visitor_name,
        "Visitor Score": int(visitor_score) if visitor_score else 0,
        "Home Team": home_name,
        "Home Score": int(home_score) if home_score else 0,
        "Status": str(status).lower(),
        "Type": str(game_type).lower()
    }

def calculate_srs_rankings(games_list):
    """Processes games, calculates capped AGD, iterates SoS, and scales top team to 99.99."""
    division_games = {}
    for g in games_list:
        if g["Status"] != "final":
            continue
        div = g["Division"]
        if not div:
            continue
        if div not in division_games:
            division_games[div] = []
        division_games[div].append(g)

    all_division_rankings = {}

    for div, games in division_games.items():
        teams = set()
        for g in games:
            teams.add(g["Home Team"])
            teams.add(g["Visitor Team"])
        teams = list(teams)
        
        if not teams:
            continue

        team_records = {t: {"W": 0, "L": 0, "T": 0, "total_gd": 0, "matchups": []} for t in teams}

        for g in games:
            home = g["Home Team"]
            visitor = g["Visitor Team"]
            h_score = g["Home Score"]
            v_score = g["Visitor Score"]

            h_diff = h_score - v_score
            v_diff = v_score - h_score

            h_diff_capped = max(-10, min(10, h_diff))
            v_diff_capped = max(-10, min(10, v_diff))

            if h_score > v_score:
                team_records[home]["W"] += 1
                team_records[visitor]["L"] += 1
            elif v_score > h_score:
                team_records[visitor]["W"] += 1
                team_records[home]["L"] += 1
            else:
                team_records[home]["T"] += 1
                team_records[visitor]["T"] += 1

            team_records[home]["total_gd"] += h_diff_capped
            team_records[visitor]["total_gd"] += v_diff_capped
            team_records[home]["matchups"].append((visitor, h_diff_capped))
            team_records[visitor]["matchups"].append((home, v_diff_capped))

        agd = {}
        for t in teams:
            gp = len(team_records[t]["matchups"])
            agd[t] = team_records[t]["total_gd"] / gp if gp > 0 else 0

        ratings = {t: agd[t] for t in teams}

        for _ in range(200):
            new_ratings = {}
            for t in teams:
                opp_ratings = [ratings[opp] for opp, _ in team_records[t]["matchups"]]
                sos = sum(opp_ratings) / len(opp_ratings) if opp_ratings else 0
                new_ratings[t] = sos + agd[t]
            ratings = new_ratings

        max_rating = max(ratings.values()) if ratings else 0
        shift = 99.99 - max_rating

        div_leaderboard = []
        for t in teams:
            final_rating = ratings[t] + shift
            final_agd = agd[t]
            final_sos = final_rating - final_agd

            w = team_records[t]["W"]
            l = team_records[t]["L"]
            t_count = team_records[t]["T"]
            wlt_string = f"{w}-{l}-{t_count}"

            div_leaderboard.append({
                "Team Name": t,
                "W-L-T": wlt_string,
                "Rating": round(final_rating, 2),
                "AGD": round(final_agd, 2),
                "SoS": round(final_sos, 2)
            })

        div_leaderboard = sorted(div_leaderboard, key=lambda x: x["Rating"], reverse=True)

        for index, item in enumerate(div_leaderboard):
            item["Rank"] = index + 1

        ordered_div_leaderboard = []
        for item in div_leaderboard:
            ordered_div_leaderboard.append({
                "Rank": item["Rank"],
                "Team Name": item["Team Name"],
                "W-L-T": item["W-L-T"],
                "Rating": item["Rating"],
                "AGD": item["AGD"],
                "SoS": item["SoS"]
            })

        all_division_rankings[div] = ordered_div_leaderboard

    return all_division_rankings

def print_rankings_preview(all_rankings):
    """
    🔍 AUDIT VISUALIZER
    Prints the actual calculated top 5 teams for every single division 
    directly into your GitHub Actions logs for validation.
    """
    print("\n" + "="*90)
    print("📋 SANITARY VERIFICATION PREVIEW - LIVE GENERATED STANDINGS")
    print("="*90)
    
    for div, teams in sorted(all_rankings.items()):
        print(f"\n🏆 DIVISION: {div} (Top 5 Snapshot)")
        print(f"{'Rank'.ljust(5)} | {'Team Name'.ljust(30)} | {'W-L-T'.ljust(8)} | {'Rating'.ljust(7)} | {'AGD'.ljust(6)} | {'SoS'}")
        print("-"*90)
        for t in teams[:5]:
            print(f"{str(t['Rank']).ljust(5)} | {t['Team Name'].ljust(30)} | {t['W-L-T'].ljust(8)} | {str(t['Rating']).ljust(7)} | {str(t['AGD']).ljust(6)} | {t['SoS']}")
    print("\n" + "="*90 + "\n")

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!")
        return
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    load_division_map()
    all_ids = list(sources.get("leagues", {}).values()) + list(sources.get("tournaments", {}).values())
    final_clean_games = []
    
    print(f"🚀 Lacrosse Data Pipeline Active. Compiling games...")

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
            pass

    print(f"✅ Downloaded and cleaned {len(final_clean_games)} total match cards.")
    print("🧮 Running iterative SRS matrix loop across all divisions...")
    rankings_output = calculate_srs_rankings(final_clean_games)
    
    # Run our new console visualizer!
    print_rankings_preview(rankings_output)
    
    # Save output locally
    output_filename = "MyLax_Rankings.json"
    with open(output_filename, 'w') as out_file:
        json.dump(rankings_output, out_file, indent=2)

if __name__ == "__main__":
    fetch_all_lacrosse_data()
