import urllib.request
import json

# 1. Your list of tournament/league API links
API_URLS = [
    "https://gamesheetstats.com/api/unified-games/14873"
    # We can paste your other links right here later, separated by commas!
]

def fetch_and_transform_data():
    all_raw_games = []

    # 2. EXTRACT: Loop through your links and download the data
    for url in API_URLS:
        print(f"Fetching data from: {url}")
        
        # We disguise Python as a normal web browser so the API doesn't block us
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req) as response:
                # Read the JSON data into Python's memory
                data = json.loads(response.read().decode())
                
                # Add these games to our master list
                if isinstance(data, list):
                    all_raw_games.extend(data)
                elif isinstance(data, dict):
                    print("Found dictionary structure, we may need to adjust!")
                    
        except Exception as e:
            print(f"Failed to pull {url} - Error: {e}")

    print(f"\n--- EXTRACTION COMPLETE ---")
    print(f"Total games downloaded into memory: {len(all_raw_games)}")
    
    # 3. TRANSFORM: This is where we will rebuild your Excel rules!
    print("\n--- TRANSFORMATION READY ---")
    
    # For now, let's just peek at the very first game to see the raw data structure
    if all_raw_games:
        print("Here is a quick look at the first raw game pulled from GameSheet:")
        # We print just the first 500 characters so it doesn't flood your screen
        print(json.dumps(all_raw_games[0], indent=2)[:500] + "\n... [cut off for space]")

# Start the engine!
fetch_and_transform_data()
