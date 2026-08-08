import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams.update({'figure.max_open_warning': 0})

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
NOTEBOOKS_DIR = os.path.dirname(__file__)

MOVIES_CSV = os.path.join(DATA_DIR, 'movies.csv')
RATINGS_CSV = os.path.join(DATA_DIR, 'ratings.csv')

def perform_eda():
    print("Loading data...")
    movies_df = pd.read_csv(MOVIES_CSV)
    ratings_df = pd.read_csv(RATINGS_CSV)
    
    # Preprocessing
    # Extract year from title (e.g. "Toy Story (1995)")
    movies_df['year'] = movies_df['title'].str.extract(r'\((\d{4})\)')
    movies_df['year'] = pd.to_numeric(movies_df['year'], errors='coerce')
    
    # Merge datasets for comprehensive analysis
    df = pd.merge(ratings_df, movies_df, on='movieId')
    
    # 1. Distribution of Movie Ratings
    print("Generating Ratings Distribution...")
    plt.figure(figsize=(10, 6))
    sns.histplot(ratings_df['rating'], bins=10, kde=False, color='#3498db')
    plt.title('Distribution of Movie Ratings', fontsize=16)
    plt.xlabel('Rating', fontsize=12)
    plt.ylabel('Count', fontsize=12)
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '01_ratings_dist.png'), bbox_inches='tight')
    plt.close()
    
    # 2. Top Genres
    print("Generating Top Genres...")
    genres_df = movies_df.copy()
    genres_df['genres'] = genres_df['genres'].str.split('|')
    genres_exploded = genres_df.explode('genres')
    genres_exploded = genres_exploded[genres_exploded['genres'] != '(no genres listed)']
    
    plt.figure(figsize=(12, 6))
    top_genres = genres_exploded['genres'].value_counts().head(15)
    sns.barplot(x=top_genres.values, y=top_genres.index, palette='viridis')
    plt.title('Top 15 Movie Genres', fontsize=16)
    plt.xlabel('Number of Movies', fontsize=12)
    plt.ylabel('Genre', fontsize=12)
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '02_top_genres.png'), bbox_inches='tight')
    plt.close()
    
    # 3. Ratings per User
    print("Generating Ratings Per User...")
    ratings_per_user = ratings_df.groupby('userId').size()
    plt.figure(figsize=(10, 6))
    sns.histplot(ratings_per_user, bins=50, kde=False, color='#e74c3c')
    plt.title('Number of Ratings Per User (Activity)', fontsize=16)
    plt.xlabel('Number of Ratings', fontsize=12)
    plt.ylabel('Number of Users', fontsize=12)
    
    # Calculate 99th percentile, ensure it's not NaN and default to 1000 if needed
    try:
        p99 = np.percentile(ratings_per_user.dropna(), 99)
        xlim_max = float(p99) if not np.isnan(p99) else 1000.0
    except:
        xlim_max = 1000.0
        
    plt.xlim(0, xlim_max) 
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '03_ratings_per_user.png'), bbox_inches='tight')
    plt.close()
    
    # 4. Ratings per Movie
    print("Generating Ratings Per Movie...")
    ratings_per_movie = ratings_df.groupby('movieId').size()
    plt.figure(figsize=(10, 6))
    sns.histplot(ratings_per_movie, bins=50, kde=False, color='#2ecc71')
    plt.title('Number of Ratings Per Movie (Popularity)', fontsize=16)
    plt.xlabel('Number of Ratings', fontsize=12)
    plt.ylabel('Number of Movies', fontsize=12)
    
    try:
        p95 = np.percentile(ratings_per_movie.dropna(), 95)
        xlim_max_movie = float(p95) if not np.isnan(p95) else 200.0
    except:
        xlim_max_movie = 200.0
        
    plt.xlim(0, xlim_max_movie)
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '04_ratings_per_movie.png'), bbox_inches='tight')
    plt.close()
    
    # 5. Average Rating vs Number of Ratings
    print("Generating Average Rating vs Number of Ratings...")
    movie_stats = df.groupby('title').agg({'rating': ['mean', 'count']})
    movie_stats.columns = ['mean_rating', 'rating_count']
    
    plt.figure(figsize=(10, 6))
    sns.jointplot(x='mean_rating', y='rating_count', data=movie_stats, alpha=0.4, color='#9b59b6', height=8)
    plt.suptitle('Average Rating vs Number of Ratings', y=1.02, fontsize=16)
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '05_avg_rating_vs_count.png'), bbox_inches='tight')
    plt.close('all')
    
    # 6. Top 15 Most Rated Movies
    print("Generating Top 15 Most Rated Movies...")
    plt.figure(figsize=(12, 8))
    top_rated_movies = movie_stats.sort_values('rating_count', ascending=False).head(15)
    sns.barplot(x=top_rated_movies['rating_count'], y=top_rated_movies.index, palette='mako')
    plt.title('Top 15 Most Rated Movies', fontsize=16)
    plt.xlabel('Number of Ratings', fontsize=12)
    plt.ylabel('Movie Title', fontsize=12)
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '06_most_rated_movies.png'), bbox_inches='tight')
    plt.close()

    # 7. Movies Release Year Distribution
    print("Generating Release Year Distribution...")
    plt.figure(figsize=(12, 6))
    valid_years = movies_df[(movies_df['year'] >= 1900) & (movies_df['year'] <= 2025)]
    sns.histplot(valid_years['year'], bins=30, color='#f39c12', kde=True)
    plt.title('Distribution of Movie Release Years', fontsize=16)
    plt.xlabel('Release Year', fontsize=12)
    plt.ylabel('Number of Movies', fontsize=12)
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '07_release_year_dist.png'), bbox_inches='tight')
    plt.close()

    # 8. Average Rating by Genre
    print("Generating Average Rating by Genre...")
    # Calculate average rating per movie first
    genre_ratings_df = pd.merge(genres_exploded, movie_stats.reset_index(), on='title', how='inner')
    
    # Get genres with at least 50 movies to ensure statistical significance
    genre_counts = genre_ratings_df['genres'].value_counts()
    valid_genres = genre_counts[genre_counts >= 50].index
    
    genre_ratings_filtered = genre_ratings_df[genre_ratings_df['genres'].isin(valid_genres)]
    avg_genre_ratings = genre_ratings_filtered.groupby('genres')['mean_rating'].mean().sort_values(ascending=False)
    
    plt.figure(figsize=(12, 8))
    sns.barplot(x=avg_genre_ratings.values, y=avg_genre_ratings.index, palette='rocket')
    plt.title('Average Movie Rating by Genre (Min 50 Movies)', fontsize=16)
    plt.xlabel('Average Rating', fontsize=12)
    plt.ylabel('Genre', fontsize=12)
    plt.xlim(2.5, 4.5)  # Zoom in on the relevant range
    plt.savefig(os.path.join(NOTEBOOKS_DIR, '08_avg_rating_by_genre.png'), bbox_inches='tight')
    plt.close()
    
    print("Comprehensive EDA completed! 8 detailed plots saved to the notebooks directory.")

if __name__ == "__main__":
    perform_eda()
