import urllib.request
import json
import os
from datetime import datetime

# Global cache for division mappings
DIVISION_MAP = {}

def load_division_map():
    global DIVISION_MAP
    if os.path.exists('divisions.json'):
        with open('divisions.json', 'r') as f:
            DIVISION_MAP = json.load(f)

def clean_team_name(name_string):
    if not name_string:
        return ""
    cleaned = name_string.strip()
    if cleaned == "Clarington Gaels 1*":
        return "Clarington Gaels 1"
    return cleaned

def format_date_string(raw_date):
    if not raw_date:
        return ""
    try:
        date_part = raw_date.split('T')[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(raw_date)

def transform_and_filter_game(game, id_number):
    visitor_obj = game.get("visitor", {})
    home_obj = game.get("home", {})
    division_obj = visitor_obj.get("division", {})

    visitor_name = visitor_obj.get("title") or ""
    home_name = home_obj.get("title") or ""
    div_name = division_obj.get("title") or game.get("divisionName") or "General"
    
    home_name = clean_team_name(home_name)
    visitor_name = clean_team_name(visitor_name)
    div_name = str(div_name).strip()

    if id_number == 15090 and div_name and not div_name.startswith("Girls "):
        div_name = f"Girls {div_name}"

    if div_name in DIVISION_MAP:
        div_name = DIVISION_MAP[div_name]

    if id_number == 14894:
        if "U9" in div_name or "U13" in div_name:
            if home_name == "Halton Hills Bulldogs": home_name = "Halton Hills Bulldogs 1"
            if visitor_name == "Halton Hills Bulldogs": visitor_name = "Halton Hills Bulldogs 1"

    raw_date = game.get("date") or ""
    clean_date = format_date_string(raw_date)
    
    visitor_score = visitor_obj.get("goals", 0)
    home_score = home_obj.get("goals", 0)
    
    raw_status = game.get("status") or "final"
    game_type = game.get("gameType") or "regular_season"

    return {
        "Date": clean_date,
        "Division": div_name,  
        "Visitor Team": visitor_name,
        "Visitor Score": int(visitor_score) if visitor_score is not None else 0,
        "Home Team": home_name,
        "Home Score": int(home_score) if home_score is not None else 0,
        "Status": str(raw_status).strip().lower(),
        "Type": str(game_type).lower()
    }

def calculate_srs_rankings(games_list):
    division_games = {}
    valid_completed_states = ["final", "official", "completed", "complete", "played", "2"]

    for g in games_list:
        if g["Status"] not in valid_completed_states:
            continue
            
        div = g["Division"]
        if not div or div == "":
            continue
        if div not in division_games:
            division_games[div] = []
        division_games[div].append(g)

    all_division_rankings = {}

    for div, games in division_games.items():
        teams = set()
        for g in games:
            if g["Home Team"]: teams.add(g["Home Team"])
            if g["Visitor Team"]: teams.add(g["Visitor Team"])
        teams = list(teams)
        
        if not teams or len(teams) < 2: 
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
                "Rating": round(final_rating, 4),
                "AGD": round(final_agd, 4),
                "SoS": round(final_sos, 4)
            })

        div_leaderboard = sorted(div_leaderboard, key=lambda x: x["Rating"], reverse=True)

        for index, item in enumerate(div_leaderboard):
            item["Rank"] = index + 1
            if index == 0:
                item["Rating"] = 99.9999

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

    # SORTING THE FINAL DICTIONARY
    custom_order = [
        "U7", "U9", "U11", "Girls U11", "U13", "Girls U13", 
        "U15", "Girls U15", "U17", "Girls U17", "U22", "Girls U22"
    ]
    order_map = {div: index for index, div in enumerate(custom_order)}
    
    sorted_rankings = {}
    for div in sorted(all_division_rankings.keys(), key=lambda x: (order_map.get(x, 999), x)):
        sorted_rankings[div] = all_division_rankings[div]

    return sorted_rankings

def fetch_all_lacrosse_data():
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found!", flush=True)
        return
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    load_division_map()
    
    all_ids = []
    ordered_tournament_names = []
    tournament_id_to_name = {}
    
    # 🧠 Initialize Smart-Mapping for Tournaments
    if isinstance(sources, dict):
        all_ids = list(sources.get("leagues", {}).values()) + list(sources.get("tournaments", {}).values())
        if not all_ids:
            all_ids = list(sources.values())
            
        if "tournaments" in sources:
            ordered_tournament_names = list(sources["tournaments"].keys())
            for name, tid in sources["tournaments"].items():
                tournament_id_to_name[tid] = name
                
    elif isinstance(sources, list):
        all_ids = sources

    print(f"🚀 Initializing Extraction. Found {len(all_ids)} GameSheet targets.", flush=True)
    final_clean_games = []
    valid_states = ["final", "official", "completed", "complete", "played", "2"]
    tournaments_with_finals = set()

    for id_number in all_ids:
        url = f"https://gamesheetstats.com/api/unified-games/{id_number}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        try:
            with urllib.request.urlopen(req) as response:
                games_list = json.loads(response.read().decode())
                
                target_list = games_list if isinstance(games_list, list) else games_list.get("games") or games_list.get("data") or []
                for game in target_list:
                    clean_item = transform_and_filter_game(game, id_number)
                    final_clean_games.append(clean_item)
                    
                    # SMART FILTER: Check if this tournament has a finalized score
                    if clean_item["Status"] in valid_states:
                        if id_number in tournament_id_to_name:
                            tournaments_with_finals.add(tournament_id_to_name[id_number])
        except Exception:
            pass

    print(f"✅ Data Extraction Complete. Total valid matches stored: {len(final_clean_games)}", flush=True)
    
    # Filter tournaments to only those with finalized scores, keeping original chronological order
    active_ordered_tournaments = [name for name in ordered_tournament_names if name in tournaments_with_finals]
    recent_tournaments = active_ordered_tournaments[-6:]
    
    # CALCULATE MOST RECENT DATE
    valid_dates = []
    for g in final_clean_games:
        if g["Status"] in valid_states and g["Date"]:
            try:
                dt = datetime.strptime(g["Date"], "%b %d, %Y")
                valid_dates.append(dt)
            except Exception:
                pass
                
    latest_date_str = "Unknown"
    if valid_dates:
        latest_date_str = max(valid_dates).strftime("%B %d, %Y")
        print(f"📅 Most recent recorded game: {latest_date_str}", flush=True)

    # WRITE METADATA JSON
    metadata = {
        "latest_game_date": latest_date_str,
        "recent_tournaments": recent_tournaments
    }
    with open("site_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("🧮 Processing 200-loop SRS matrix rankings...", flush=True)
    rankings_output = calculate_srs_rankings(final_clean_games)
    
    with open("MyLax_Rankings.json", 'w') as out_file:
        json.dump(rankings_output, out_file, indent=2)

    # --- ROLLING 6-DAY HISTORY WITH RANK AND RATING PROFILE ---
    history_file = "rankings_history.json"
    history_data = {}
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as hf:
                history_data = json.load(hf)
        except Exception:
            history_data = {}

    today_key = datetime.now().strftime("%Y-%m-%d")
    today_map = {}
    
    # Pack both Rank and Rating into the daily snapshot profile
    for div, teams in rankings_output.items():
        today_map[div] = {t["Team Name"]: {"Rank": t["Rank"], "Rating": t["Rating"]} for t in teams}
        
    history_data[today_key] = today_map

    sorted_history_days = sorted(history_data.keys())
    while len(sorted_history_days) > 6:
        oldest_day = sorted_history_days.pop(0)
        history_data.pop(oldest_day, None)

    with open(history_file, 'w') as hf:
        json.dump(history_data, hf, indent=2)
    print(f"📦 Advanced profile history log updated. Days archived: {len(history_data)}/6", flush=True)

if __name__ == "__main__":
    fetch_all_lacrosse_data()
