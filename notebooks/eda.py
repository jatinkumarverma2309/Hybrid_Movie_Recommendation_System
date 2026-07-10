import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_theme(style="whitegrid")

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
    
    print("Generating Ratings Distribution...")
    plt.figure(figsize=(10, 6))
    sns.histplot(ratings_df['rating'], bins=10, kde=False, color='skyblue')
    plt.title('Distribution of Movie Ratings')
    plt.xlabel('Rating')
    plt.ylabel('Count')
    plt.savefig(os.path.join(NOTEBOOKS_DIR, 'ratings_dist.png'))
    plt.close()
    
    print("Generating Top Genres...")
    # Explode genres
    genres_df = movies_df.copy()
    genres_df['genres'] = genres_df['genres'].str.split('|')
    genres_exploded = genres_df.explode('genres')
    
    plt.figure(figsize=(12, 6))
    top_genres = genres_exploded['genres'].value_counts().head(15)
    sns.barplot(x=top_genres.values, y=top_genres.index, palette='viridis')
    plt.title('Top 15 Movie Genres')
    plt.xlabel('Number of Movies')
    plt.ylabel('Genre')
    plt.savefig(os.path.join(NOTEBOOKS_DIR, 'top_genres.png'))
    plt.close()
    
    print("Generating Ratings Per User...")
    ratings_per_user = ratings_df.groupby('userId').size()
    plt.figure(figsize=(10, 6))
    sns.histplot(ratings_per_user, bins=50, kde=False, color='salmon')
    plt.title('Number of Ratings Per User')
    plt.xlabel('Number of Ratings')
    plt.ylabel('Number of Users')
    plt.xlim(0, 1000) # limit to 1000 for better view
    plt.savefig(os.path.join(NOTEBOOKS_DIR, 'ratings_per_user.png'))
    plt.close()
    
    print("EDA completed! Plots saved to the notebooks directory.")

if __name__ == "__main__":
    perform_eda()
