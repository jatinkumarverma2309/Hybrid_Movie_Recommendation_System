import os
import pandas as pd
import requests
from dotenv import load_dotenv
import time
import concurrent.futures

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_CSV_PATH = os.path.join(BASE_DIR, 'data', 'movies_enriched.csv')

def get_movie_details(tmdb_id):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=videos,credits"
    for attempt in range(3):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                details = res.json()
                poster_path = details.get('poster_path')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                
                trailer_url = None
                videos = details.get('videos', {}).get('results', [])
                for video in videos:
                    if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                        trailer_url = f"https://www.youtube.com/watch?v={video.get('key')}"
                        break
                
                cast = details.get('credits', {}).get('cast', [])
                top_cast = [c.get('name') for c in cast[:3]]
                
                genres_list = [g.get('name') for g in details.get('genres', [])]
                
                return {
                    'tmdbId': int(tmdb_id),
                    'imdbId': details.get('imdb_id', ''),
                    'title': details.get('title', ''),
                    'genres': "|".join(genres_list) if genres_list else "Unknown",
                    'overview': details.get('overview', ''),
                    'poster_url': poster_url,
                    'trailer_url': trailer_url,
                    'cast': ", ".join(top_cast) if top_cast else ""
                }
        except Exception:
            time.sleep(1)
    return None

def main():
    print("Loading existing dataset...")
    df = pd.read_csv(OUTPUT_CSV_PATH)
    existing_tmdb_ids = set(df['tmdbId'].dropna().astype(int))
    
    next_movie_id = int(df['movieId'].max()) + 1
    
    new_tmdb_ids = set()
    
    # 1. Search for specific movies (Interstellar)
    queries = ["Interstellar"]
    for q in queries:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={q}"
        try:
            res = requests.get(url).json()
            if res.get('results'):
                top_id = res['results'][0]['id']
                if top_id not in existing_tmdb_ids:
                    new_tmdb_ids.add(top_id)
        except Exception as e:
            print(f"Error searching for {q}: {e}")
            
    # 2. Grab popular movies
    print("Fetching popular movies...")
    for page in range(1, 21):
        url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&page={page}"
        try:
            res = requests.get(url).json()
            for m in res.get('results', []):
                m_id = m['id']
                if m_id not in existing_tmdb_ids:
                    new_tmdb_ids.add(m_id)
        except Exception:
            pass
            
    # 3. Grab trending this week
    print("Fetching trending movies...")
    for page in range(1, 21):
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}&page={page}"
        try:
            res = requests.get(url).json()
            for m in res.get('results', []):
                m_id = m['id']
                if m_id not in existing_tmdb_ids:
                    new_tmdb_ids.add(m_id)
        except Exception:
            pass
            
    # Also fetch upcoming and now playing
    for endpoint in ['upcoming', 'now_playing']:
        for page in range(1, 6):
            url = f"https://api.themoviedb.org/3/movie/{endpoint}?api_key={TMDB_API_KEY}&page={page}"
            try:
                res = requests.get(url).json()
                for m in res.get('results', []):
                    m_id = m['id']
                    if m_id not in existing_tmdb_ids:
                        new_tmdb_ids.add(m_id)
            except Exception:
                pass
                
    new_tmdb_ids = list(new_tmdb_ids)
    print(f"Found {len(new_tmdb_ids)} new movies to inject.")
    
    if not new_tmdb_ids:
        print("No new movies to add.")
        return
        
    enriched_data = []
    print("Fetching details multi-threaded...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_movie_details, t_id): t_id for t_id in new_tmdb_ids}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                res['movieId'] = next_movie_id
                next_movie_id += 1
                enriched_data.append(res)
            completed += 1
            if completed % 100 == 0:
                print(f"Processed {completed}/{len(new_tmdb_ids)}")
                
    new_df = pd.DataFrame(enriched_data)
    
    # Merge and save
    combined_df = pd.concat([df, new_df], ignore_index=True)
    combined_df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"Successfully injected {len(new_df)} movies into the database.")

if __name__ == "__main__":
    main()
