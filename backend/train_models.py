import os
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from surprise import Reader, Dataset, SVD

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'backend', 'models')

MOVIES_ENRICHED_CSV = os.path.join(DATA_DIR, 'movies_enriched.csv')
MOVIES_BASE_CSV = os.path.join(DATA_DIR, 'movies.csv')
RATINGS_CSV = os.path.join(DATA_DIR, 'ratings.csv')

def create_soup(x):
    genres = str(x.get('genres', '')).replace('|', ' ')
    cast = str(x.get('cast', '')).replace(',', '')
    overview = str(x.get('overview', ''))
    return f"{genres} {cast} {overview}"

def train_content_based(movies_df):
    print("Training Content-Based Model (TF-IDF)...")
    movies_df['soup'] = movies_df.apply(create_soup, axis=1)
    
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(movies_df['soup'])
    
    joblib.dump(tfidf, os.path.join(MODELS_DIR, 'tfidf_vectorizer.joblib'))
    joblib.dump(tfidf_matrix, os.path.join(MODELS_DIR, 'tfidf_matrix.joblib'))
    
    # Save a lightweight version of movies dataframe for fast lookup
    movies_df.to_pickle(os.path.join(MODELS_DIR, 'movies_df.pkl'))
    
    print("Content-based model saved.")

def train_collaborative(ratings_df):
    print("Training Collaborative Filtering Model (SVD)...")
    reader = Reader(rating_scale=(0.5, 5.0))
    data = Dataset.load_from_df(ratings_df[['userId', 'movieId', 'rating']], reader)
    
    trainset = data.build_full_trainset()
    svd_model = SVD(n_epochs=20, lr_all=0.005, reg_all=0.02)
    svd_model.fit(trainset)
    
    joblib.dump(svd_model, os.path.join(MODELS_DIR, 'svd_model.joblib'))
    print("Collaborative model saved.")

def run_training():
    print("Loading data for training...")
    # Prefer enriched, fallback to base
    if os.path.exists(MOVIES_ENRICHED_CSV):
        movies_df = pd.read_csv(MOVIES_ENRICHED_CSV)
        print(f"Using enriched movies data ({len(movies_df)} rows).")
    else:
        movies_df = pd.read_csv(MOVIES_BASE_CSV)
        print("Enriched data not found. Using base movies data.")
        
    for col in ['genres', 'overview', 'cast']:
        if col in movies_df.columns:
            movies_df[col] = movies_df[col].fillna('')
            
    ratings_df = pd.read_csv(RATINGS_CSV)
    
    train_content_based(movies_df)
    train_collaborative(ratings_df)
    
    print("\nAll models trained and saved successfully in 'backend/models/'")

if __name__ == "__main__":
    run_training()
