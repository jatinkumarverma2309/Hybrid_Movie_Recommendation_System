import os
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics.pairwise import linear_kernel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'backend', 'models')

class RecommenderSystem:
    def __init__(self):
        self.movies_df: pd.DataFrame | None = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.svd_model = None
        self.indices: pd.Series | None = None
        self.id_indices: pd.Series | None = None
        
        self._load_models()

    def _load_models(self):
        print("Loading pre-trained models and data...")
        try:
            self.movies_df = pd.read_pickle(os.path.join(MODELS_DIR, 'movies_df.pkl'))
            self.tfidf_vectorizer = joblib.load(os.path.join(MODELS_DIR, 'tfidf_vectorizer.joblib'))
            self.tfidf_matrix = joblib.load(os.path.join(MODELS_DIR, 'tfidf_matrix.joblib'))
            self.svd_model = joblib.load(os.path.join(MODELS_DIR, 'svd_model.joblib'))
            
            # Create indices mapping
            self.indices = pd.Series(self.movies_df.index, index=self.movies_df['title']).drop_duplicates()
            self.id_indices = pd.Series(self.movies_df.index, index=self.movies_df['movieId']).drop_duplicates()
            
            # Keep ratings mapping for collaborative filtering filtering
            # For a real large-scale app, we might query a DB, but for now we load it.
            self.ratings_df = pd.read_csv(os.path.join(DATA_DIR, 'ratings.csv'))
            
            print("Models loaded successfully.")
        except Exception as e:
            print(f"Error loading models: {e}")
            print("Please run `python train_models.py` to generate the models first.")

    def get_content_based_recommendations(self, title=None, movie_id=None, top_n=10):
        if title and title in self.indices:
            idx = self.indices[title]
        elif movie_id and movie_id in self.id_indices:
            idx = self.id_indices[movie_id]
        else:
            return []
            
        # Compute cosine similarity for just this ONE movie against all others
        # This is extremely fast and saves RAM vs storing 9700x9700 dense matrix
        sim_scores = linear_kernel(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        
        # Get top N indices (excluding the movie itself)
        # argsort sorts ascending, so we take the end and reverse it
        top_indices = sim_scores.argsort()[-(top_n+1):][::-1]
        
        # Filter out the movie itself
        movie_indices = [i for i in top_indices if i != idx][:top_n]
        
        return self.movies_df.iloc[movie_indices].to_dict('records')

    def get_collaborative_recommendations(self, user_id, top_n=10):
        all_movie_ids = self.movies_df['movieId'].tolist()
        user_rated_movies = self.ratings_df[self.ratings_df['userId'] == user_id]['movieId'].tolist()
        unrated_movies = [m for m in all_movie_ids if m not in user_rated_movies]
        
        predictions = []
        for m_id in unrated_movies:
            pred = self.svd_model.predict(user_id, m_id)
            predictions.append((m_id, pred.est))
            
        import random
        predictions.sort(key=lambda x: x[1], reverse=True)
        top_100_movie_ids = [x[0] for x in predictions[:100]]
        
        # Refresh by sampling
        sampled_ids = random.sample(top_100_movie_ids, min(top_n, len(top_100_movie_ids)))
        
        return self.movies_df[self.movies_df['movieId'].isin(sampled_ids)].to_dict('records')

    def get_hybrid_recommendations(self, user_id, movie_id=None, top_n=10):
        if not movie_id:
            return self.get_collaborative_recommendations(user_id, top_n)
            
        similar_movies = self.get_content_based_recommendations(movie_id=movie_id, top_n=50)
        
        hybrid_scores = []
        for movie in similar_movies:
            m_id = movie['movieId']
            pred = self.svd_model.predict(user_id, m_id)
            hybrid_scores.append((movie, pred.est))
            
        hybrid_scores.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in hybrid_scores[:top_n]]

    def get_semantic_search_recommendations(self, query: str, top_n=5):
        if not self.tfidf_vectorizer or not query.strip():
            return []
            
        # Vectorize the user's natural language query
        query_vec = self.tfidf_vectorizer.transform([query])
        
        # Compute cosine similarity against all movies
        sim_scores = linear_kernel(query_vec, self.tfidf_matrix).flatten()
        
        # Get top N matches
        top_indices = sim_scores.argsort()[-top_n:][::-1]
        
        return self.movies_df.iloc[top_indices].to_dict('records')

recommender = None

def get_recommender():
    global recommender
    if recommender is None:
        recommender = RecommenderSystem()
    return recommender
