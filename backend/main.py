from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Any
from pydantic import BaseModel
from google.oauth2 import id_token # type: ignore
from google.auth.transport import requests as google_requests # type: ignore
import requests
import google.generativeai as genai
import pandas as pd
import numpy as np
import os
import uuid
import shutil
import bcrypt
import jwt
from rapidfuzz import process, fuzz, utils

import database as db
from recommender import get_recommender

app = FastAPI(title="Hybrid Movie Recommender API")

# Ensure uploads directory exists before mounting
uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

# Setup CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://moviematch-six-mocha.vercel.app",
        "http://localhost:5173", 
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Movie(BaseModel):
    movieId: int
    title: str
    genres: str
    tmdbId: Any = None
    imdbId: Any = None
    overview: Any = None
    poster_url: Any = None
    trailer_url: Any = None
    cast: Any = None

@app.on_event("startup")
async def startup_event():
    # Initialize recommender (loads models)
    get_recommender()
    # Initialize database
    db.init_db()

# Mount uploads directory for static serving
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

@app.get("/")
def root():
    return {"message": "Welcome to the Hybrid Movie Recommender API"}

class TokenData(BaseModel):
    token: str


SECRET_KEY = "my_super_secret_jwt_key_movie_match"
ALGORITHM = "HS256"

class AuthUser(BaseModel):
    name: str
    email: str
    password: str

class LoginUser(BaseModel):
    email: str
    password: str

@app.post("/auth/register")
def register(user: AuthUser):
    existing = db.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user id simulating a sub ID format
    user_id = str(uuid.uuid4().int)[:15] 
    hashed_pwd = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.create_native_user(user_id, user.email, hashed_pwd, user.name)
    
    # Generate token matching Google's decoded format structure
    token = jwt.encode({"sub": user_id, "name": user.name, "email": user.email, "picture": None, "is_admin": False}, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "user": {"user_id": user_id, "name": user.name, "email": user.email, "is_admin": False}}

@app.post("/auth/login")
def login(user: LoginUser):
    db_user = db.get_user_by_email(user.email)
    if not db_user or not db_user['password_hash'] or not bcrypt.checkpw(user.password.encode('utf-8'), db_user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    token = jwt.encode({
        "sub": db_user['user_id'], 
        "name": db_user['name'], 
        "email": db_user['email'], 
        "picture": db_user['profile_picture_url'],
        "is_admin": db_user.get('is_admin', False)
    }, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "user": {"user_id": db_user['user_id'], "name": db_user['name'], "email": db_user['email'], "picture": db_user['profile_picture_url'], "is_admin": db_user.get('is_admin', False)}}

@app.post("/auth/verify")
def verify_token(data: TokenData):
    try:
        # First try to verify as native JWT
        try:
            payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
            return {"user_id": payload['sub'], "email": payload.get('email'), "name": payload.get('name'), "picture": payload.get('picture'), "is_admin": payload.get('is_admin', False)}
        except jwt.PyJWTError:
            pass # Fallback to Google verification
            
        # Verify the token using Google's library
        user_info = id_token.verify_oauth2_token(data.token, google_requests.Request())
        return {"user_id": user_info['sub'], "email": user_info.get('email')}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
def clean_results(df_or_list):
    if isinstance(df_or_list, pd.DataFrame):
        df_or_list = df_or_list.where(pd.notnull(df_or_list), None)
        return df_or_list.to_dict('records')
    elif isinstance(df_or_list, list):
        # Already a list of dicts from recommender
        # Just replace nan with None in dicts
        cleaned = []
        for d in df_or_list:
            cleaned.append({k: (None if pd.isna(v) else v) for k, v in d.items()})
        return cleaned
    return df_or_list

@app.get("/movie/{tmdb_id}/details")
def get_movie_details(tmdb_id: int):
    # Fetch live rating and runtime from TMDB
    tmdb_key = os.getenv("TMDB_API_KEY")
    if not tmdb_key:
        return {"vote_average": None, "runtime": None}
    
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={tmdb_key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "vote_average": data.get("vote_average"),
                "runtime": data.get("runtime")
            }
    except Exception:
        pass
        
    return {"vote_average": None, "runtime": None}

@app.get("/movies/search", response_model=List[Movie])
def search_movies(q: str = Query(..., min_length=2), limit: int = 10):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    titles = rec.movies_df['title'].dropna().tolist()
    
    # WRatio is excellent for handling typos, partial matches, and different casing
    matches = process.extract(q, titles, limit=limit*2, scorer=fuzz.WRatio, processor=utils.default_process)
    
    # Keep matches with a reasonable score threshold and ensure uniqueness
    seen = set()
    matched_titles = []
    for m in matches:
        if m[1] > 50 and m[0] not in seen:
            seen.add(m[0])
            matched_titles.append(m[0])
            if len(matched_titles) == limit:
                break
    
    if not matched_titles:
        return []
        
    results = rec.movies_df[rec.movies_df['title'].isin(matched_titles)].copy()
    
    # Sort the dataframe by the fuzzy match score order
    results['title_cat'] = pd.Categorical(results['title'], categories=matched_titles, ordered=True)
    results = results.sort_values('title_cat').drop('title_cat', axis=1)
    
    return clean_results(results)
    
@app.get("/movies/popular", response_model=List[Movie])
def popular_movies(limit: int = 20):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    # The newly injected trending movies are at the end of the dataset
    return clean_results(rec.movies_df.tail(100).sample(limit))

@app.get("/movies/latest", response_model=List[Movie])
def latest_movies(limit: int = 20):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    # The absolute newest movies are at the very end
    df = rec.movies_df.copy()
    latest_subset = df.iloc[::-1].head(limit)
    return clean_results(latest_subset)

@app.get("/recommend/content", response_model=List[Movie])
def recommend_content(title: Optional[str] = None, movie_id: Optional[int] = None, limit: int = 10):
    if not title and not movie_id:
        raise HTTPException(status_code=400, detail="Must provide either title or movie_id")
        
    rec = get_recommender()
    results = rec.get_content_based_recommendations(title=title, movie_id=movie_id, top_n=limit)
    return clean_results(results)

@app.get("/recommend/collaborative", response_model=List[Movie])
def recommend_collaborative(user_id: str, limit: int = 10):
    rec = get_recommender()
    results = rec.get_collaborative_recommendations(user_id=user_id, top_n=limit)
    return clean_results(results)

@app.get("/recommend/hybrid", response_model=List[Movie])
def recommend_hybrid(user_id: str, movie_id: int, limit: int = 10):
    rec = get_recommender()
    results = rec.get_hybrid_recommendations(user_id=user_id, movie_id=movie_id, top_n=limit)
    return clean_results(results)

@app.get("/watchlist", response_model=List[Movie])
def get_user_watchlist(user_id: str):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    movie_ids = db.get_watchlist(str(user_id))
    results = rec.movies_df[rec.movies_df['movieId'].isin(movie_ids)]
    return clean_results(results)

@app.post("/watchlist/{movie_id}")
def add_movie_to_watchlist(user_id: str, movie_id: int):
    db.add_to_watchlist(str(user_id), movie_id)
    return {"status": "success"}

@app.delete("/watchlist/{movie_id}")
def remove_movie_from_watchlist(user_id: str, movie_id: int):
    db.remove_from_watchlist(str(user_id), movie_id)
    return {"status": "success"}

@app.get("/favorites", response_model=List[Movie])
def get_user_favorites(user_id: str):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    movie_ids = db.get_favorites(str(user_id))
    results = rec.movies_df[rec.movies_df['movieId'].isin(movie_ids)]
    return clean_results(results)

@app.post("/favorites/{movie_id}")
def add_movie_to_favorites(user_id: str, movie_id: int):
    db.add_to_favorites(str(user_id), movie_id)
    return {"status": "success"}

@app.delete("/favorites/{movie_id}")
def remove_movie_from_favorites(user_id: str, movie_id: int):
    db.remove_from_favorites(str(user_id), movie_id)
    return {"status": "success"}

@app.get("/profile/{user_id}")
def get_user_profile(user_id: str):
    profile = db.get_user_profile(str(user_id))
    if not profile:
        profile = {}
        
    movie_ids = db.get_favorites(str(user_id))
    rec = get_recommender()
    if rec.movies_df is not None and movie_ids:
        fav_movies = rec.movies_df[rec.movies_df['movieId'].isin(movie_ids)]
        all_genres = fav_movies['genres'].dropna().str.split('|').explode()
        if not all_genres.empty:
            profile['favourite_genre'] = all_genres.value_counts().index[0]
            
    return profile

@app.post("/profile/picture")
async def upload_profile_picture(user_id: str = Form(...), file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = filename.split('.')[-1] if '.' in filename else 'jpg'
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(os.path.dirname(__file__), 'uploads', filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    url = f"http://localhost:8000/uploads/{filename}"
    db.upsert_user_profile_picture(str(user_id), url)
    
    return {"profile_picture_url": url}

@app.delete("/profile/{user_id}/picture")
def remove_profile_picture(user_id: str):
    db.delete_user_profile_picture(user_id)
    return {"status": "success"}

class ProfileNameUpdate(BaseModel):
    name: str

@app.post("/profile/{user_id}/name")
def update_profile_name(user_id: str, payload: ProfileNameUpdate):
    db.update_user_name(str(user_id), payload.name)
    return {"status": "success"}

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
def chat_with_bot(req: ChatRequest):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        movies = rec.get_semantic_search_recommendations(req.query, top_n=5)
        if not movies:
            return {"message": "I'm sorry, I couldn't find any movies matching that description.", "movies": []}
        return {"message": "Here are some movies I found that match your description:", "movies": clean_results(movies)}
        
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are MovieMatch AI, a helpful movie recommendation assistant. 
        The user is asking: "{req.query}"
        
        Respond with a friendly conversational message answering their question, followed by a JSON array of up to 5 exact movie titles that best match their request.
        Do NOT include any formatting markdown like ```json. Output exactly in this raw JSON format:
        {{
            "message": "Your friendly response here...",
            "movie_titles": ["Title 1", "Title 2"]
        }}
        """
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        import json
        data = json.loads(content)
        
        titles = data.get("movie_titles", [])
        
        found_movies = []
        all_titles = rec.movies_df['title'].dropna().tolist()
        for t in titles:
            match = process.extractOne(t, all_titles, scorer=fuzz.WRatio, processor=utils.default_process)
            if match and match[1] > 60:
                matched_title = match[0]
                matches = rec.movies_df[rec.movies_df['title'] == matched_title]
                if not matches.empty:
                    found_movies.append(matches.iloc[0].to_dict())
                
        if not found_movies:
            found_movies = rec.get_semantic_search_recommendations(req.query, top_n=5)
             
        return {
            "message": data.get("message", "Here are some recommendations:"),
            "movies": clean_results(found_movies[:5])
        }
    except Exception as e:
        print(f"Gemini error: {e}")
        movies = rec.get_semantic_search_recommendations(req.query, top_n=5)
        return {"message": "I had a minor hiccup reaching the AI server, but here is what my local engine found:", "movies": clean_results(movies)}

# --- TRACKING & ANALYTICS ---

class TrackSearch(BaseModel):
    user_id: str
    query: str

@app.post("/track/search")
def track_search(data: TrackSearch):
    db.log_search(data.user_id, data.query)
    return {"status": "success"}

class TrackView(BaseModel):
    user_id: str
    movie_id: int

@app.post("/track/view")
def track_view(data: TrackView):
    db.log_movie_view(data.user_id, data.movie_id)
    return {"status": "success"}

class TrackRec(BaseModel):
    user_id: str
    rec_type: str

@app.post("/track/recommend")
def track_recommendation(data: TrackRec):
    db.log_recommendation(data.user_id, data.rec_type)
    return {"status": "success"}

@app.get("/history/searches")
def get_search_history(user_id: str):
    return db.get_recent_searches(user_id)

@app.get("/analytics/dashboard")
def get_analytics_dashboard(user_id: str):
    is_admin = db.check_is_admin(user_id)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    admin_stats = db.get_admin_stats()
    
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    # Calculate Genre Distribution
    all_genres = rec.movies_df['genres'].dropna().str.split('|').explode()
    genre_counts = all_genres.value_counts().head(10).to_dict()
    genre_dist = [{"name": k, "value": v} for k, v in genre_counts.items() if k != '(no genres listed)']
    
    # Calculate Ratings Distribution
    rating_counts = rec.ratings_df['rating'].value_counts().sort_index().to_dict()
    ratings_dist = [{"rating": str(k), "count": v} for k, v in rating_counts.items()]
    
    # Calculate Top Actors
    all_cast = rec.movies_df['cast'].dropna().str.split(',').explode().str.strip()
    cast_counts = all_cast.value_counts().head(10).to_dict()
    top_actors = [{"name": k, "count": v} for k, v in cast_counts.items()]
    
    # Most viewed movie title
    most_viewed_title = "N/A"
    if admin_stats['most_viewed_movie_id']:
        row = rec.movies_df[rec.movies_df['movieId'] == admin_stats['most_viewed_movie_id']]
        if not row.empty:
            most_viewed_title = row.iloc[0]['title']
            
    admin_stats['most_viewed_movie_title'] = most_viewed_title
    
    # Format rec types
    rec_types_formatted = [{"name": k, "value": v} for k, v in admin_stats['recommendation_types'].items()]

    return {
        "stats": admin_stats,
        "charts": {
            "genres": genre_dist,
            "ratings": ratings_dist,
            "actors": top_actors,
            "recommendations": rec_types_formatted
        }
    }

@app.get("/movies/mood", response_model=List[Movie])
def mood_recommendations(mood: str, limit: int = 20):
    rec = get_recommender()
    if rec.movies_df is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
        
    mood_map = {
        "happy": "Comedy|Family|Animation",
        "thrilling": "Action|Thriller|Sci-Fi",
        "scary": "Horror|Mystery",
        "romantic": "Romance|Drama",
        "sad": "Drama",
        "adventurous": "Adventure|Fantasy"
    }
    
    genres = mood_map.get(mood.lower())
    if not genres:
        return []
        
    pattern = genres
    results = rec.movies_df[rec.movies_df['genres'].str.contains(pattern, case=False, na=False, regex=True)]
    
    if len(results) > 0:
        results = results.sample(n=min(limit, len(results)))
        
    return clean_results(results.head(limit))
