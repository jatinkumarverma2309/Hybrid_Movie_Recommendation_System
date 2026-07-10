import os
import pandas as pd
import requests
from dotenv import load_dotenv
import time
import concurrent.futures
import datetime

# Load environment variables
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY or TMDB_API_KEY == "YOUR_TMDB_API_KEY_HERE":
    print("Please set your TMDB_API_KEY in the .env file.")
    exit(1)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LINKS_CSV_PATH = os.path.join(DATA_DIR, 'links.csv')
MOVIES_CSV_PATH = os.path.join(DATA_DIR, 'movies.csv')
OUTPUT_CSV_PATH = os.path.join(DATA_DIR, 'movies_enriched.csv')

def discover_popular_movies(target_count, existing_tmdb_ids):
    print(f"Discovering up to {target_count} additional popular movies from TMDB...")
    new_movies = []
    
    current_year = datetime.datetime.now().year
    year = current_year
    pages_per_year = 500
    
    while len(new_movies) < target_count:
        for page in range(1, pages_per_year + 1):
            if len(new_movies) >= target_count:
                break
                
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&sort_by=popularity.desc&primary_release_year={year}&page={page}"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    if not results:
                        break # no more pages for this year
                        
                    for m in results:
                        tmdb_id = m.get('id')
                        if tmdb_id and tmdb_id not in existing_tmdb_ids:
                            existing_tmdb_ids.add(tmdb_id)
                            
                            new_movies.append({
                                'tmdbId': tmdb_id,
                                'title': m.get('title', ''),
                                'genres': '' # Will be fetched in details
                            })
                            if len(new_movies) >= target_count:
                                break
                elif response.status_code == 429:
                    time.sleep(2)
                else:
                    break # other error, move to next year
            except requests.exceptions.RequestException:
                time.sleep(1)
                
        year -= 1
        if year < 1900:
            break
            
    print(f"Discovered {len(new_movies)} new movies.")
    return new_movies

def fetch_movie_details(row):
    tmdb_id = row.get('tmdbId')
    if pd.isna(tmdb_id) if isinstance(tmdb_id, float) else tmdb_id is None:
        return None
    
    tmdb_id = int(tmdb_id)
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=videos,credits"
    
    # Retry mechanism for connection resets
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                details = response.json()
                
                poster_path = details.get('poster_path')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                overview = details.get('overview', '')
                
                trailer_url = None
                videos = details.get('videos', {}).get('results', [])
                for video in videos:
                    if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                        trailer_url = f"https://www.youtube.com/watch?v={video.get('key')}"
                        break
                
                cast = details.get('credits', {}).get('cast', [])
                top_cast = [c.get('name') for c in cast[:3]]
                
                genres = row.get('genres', '')
                if not genres and 'genres' in details:
                    genres = "|".join([g['name'] for g in details['genres']])
                
                return {
                    'movieId': row['movieId'],
                    'title': row['title'],
                    'genres': genres,
                    'tmdbId': tmdb_id,
                    'imdbId': row.get('imdbId', ''),
                    'overview': overview,
                    'poster_url': poster_url,
                    'trailer_url': trailer_url,
                    'cast': ", ".join(top_cast)
                }
            elif response.status_code == 429: # Rate Limit
                time.sleep(2)
            else:
                break # Other error like 404
        except requests.exceptions.RequestException:
            time.sleep(1) # Wait before retry
            
    return None

def process_movies(limit=None, target_total=30000):
    print("Loading base datasets...")
    links_df = pd.read_csv(LINKS_CSV_PATH)
    movies_df = pd.read_csv(MOVIES_CSV_PATH)
    
    df = pd.merge(movies_df, links_df, on='movieId')
    
    movies_to_process = []
    existing_tmdb_ids = set()
    
    for _, row in df.iterrows():
        tmdb_id = row['tmdbId']
        if pd.notna(tmdb_id):
            existing_tmdb_ids.add(int(tmdb_id))
            movies_to_process.append({
                'movieId': row['movieId'],
                'title': row['title'],
                'genres': row['genres'],
                'tmdbId': int(tmdb_id),
                'imdbId': row.get('imdbId')
            })
            
    if limit:
        movies_to_process = movies_to_process[:limit]
        target_total = limit
        
    needed_count = target_total - len(movies_to_process)
    
    if needed_count > 0:
        new_discovered = discover_popular_movies(needed_count, existing_tmdb_ids)
        
        next_mock_id = df['movieId'].max() + 1
        if pd.isna(next_mock_id): next_mock_id = 1000000
        
        for m in new_discovered:
            m['movieId'] = int(next_mock_id)
            m['imdbId'] = ''
            movies_to_process.append(m)
            next_mock_id += 1
            
    total = len(movies_to_process)
    print(f"Fetching full details for {total} movies using multi-threading...")
    
    enriched_data = []
    
    # Use ThreadPoolExecutor to speed up fetching dramatically
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_movie_details, row): row for row in movies_to_process}
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                enriched_data.append(result)
                
            completed += 1
            if completed % 100 == 0:
                print(f"Processed {completed}/{total}")

    enriched_df = pd.DataFrame(enriched_data)
    enriched_df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"Enriched data saved to {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    # Target up to 30000 movies
    process_movies(limit=None, target_total=30000)
