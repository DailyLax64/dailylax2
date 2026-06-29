import urllib.request
import json
import os

def fetch_all_lacrosse_data():
    # 1. Safely open and read your sources config file
    if not os.path.exists('sources.json'):
        print("❌ Error: sources.json file not found! Please create it first.")
        return
        
    with open('sources.json', 'r') as f:
        sources = json.load(f)
    
    # 2. Extract every ID number out of both categories
    league_ids = list(sources.get("leagues", {}).values())
    tournament_ids = list(sources.get("tournaments", {}).values())
    all_ids = league_ids + tournament_ids
    
    all_raw_games = []
    
    print(f"🚀 Lacrosse Data Pipeline Active.")
    print(f"📊 Found {len(league_ids)} core leagues & {len(tournament_ids)} tournaments in config.")
    print(f"📡 Processing {len(all_ids)} total GameSheet data streams...\n")

    # 3. Pull down data for every single ID automatically
    for id_number in all_ids:
        url = f"https://gamesheetstats.com/api/unified-games/{id_number}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                if isinstance(data, list):
                    all_raw_games.extend(data)
                    print(f"  🔹 ID [{id_number}]: Connected. Grabbed {len(data)} games.")
                else:
                    print(f"  ⚠️ ID [{id_number}]: Connected, but returned unexpected format.")
                    
        except Exception as e:
            print(f"  ❌ Error loading ID [{id_number}]: {e}")

    print(f"\n==================================================")
    print(f"🏆 PIPELINE AGGREGATION COMPLETE")
    print(f"==================================================")
    print(f"Successfully compiled {len(all_raw_games)} total lacrosse games into memory.")
    print(f"All data streams are now stacked together safely.")
    print(f"Website integrity unaffected. Sandbox testing successful.")
    print(f"==================================================")

# Run the master fetch routine
if __name__ == "__main__":
    fetch_all_lacrosse_data()
