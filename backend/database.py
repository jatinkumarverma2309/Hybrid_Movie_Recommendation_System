import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

from psycopg2 import pool

db_pool = None
if DATABASE_URL:
    try:
        db_pool = pool.ThreadedConnectionPool(1, 20, DATABASE_URL)
    except Exception as e:
        print(f"Error creating connection pool: {e}")

class PooledConnection:
    def __init__(self):
        if not db_pool:
            raise ValueError("DATABASE_URL environment variable is not set or pool failed to initialize.")
        self.conn = db_pool.getconn()
    def cursor(self, *args, **kwargs):
        return self.conn.cursor(*args, **kwargs)
    def commit(self):
        self.conn.commit()
    def rollback(self):
        self.conn.rollback()
    def close(self):
        db_pool.putconn(self.conn)

def get_db_connection():
    return PooledConnection()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Watchlist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            user_id TEXT,
            movie_id INTEGER,
            PRIMARY KEY (user_id, movie_id)
        )
    ''')
    
    # Favorites table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id TEXT,
            movie_id INTEGER,
            PRIMARY KEY (user_id, movie_id)
        )
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            profile_picture_url TEXT
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT UNIQUE")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE")
    except Exception as e:
        pass
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            query TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movie_views (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            movie_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendation_logs (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            rec_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

def add_to_watchlist(user_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO watchlist (user_id, movie_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, movie_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def remove_from_watchlist(user_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM watchlist WHERE user_id = %s AND movie_id = %s', (user_id, movie_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_watchlist(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT movie_id FROM watchlist WHERE user_id = %s', (user_id,))
        movies = [row[0] for row in cursor.fetchall()]
        return movies
    finally:
        cursor.close()
        conn.close()

def add_to_favorites(user_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO favorites (user_id, movie_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_id, movie_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def remove_from_favorites(user_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM favorites WHERE user_id = %s AND movie_id = %s', (user_id, movie_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_favorites(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT movie_id FROM favorites WHERE user_id = %s', (user_id,))
        movies = [row[0] for row in cursor.fetchall()]
        return movies
    finally:
        cursor.close()
        conn.close()

def upsert_user_profile_picture(user_id, picture_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, profile_picture_url) 
            VALUES (%s, %s) 
            ON CONFLICT (user_id) 
            DO UPDATE SET profile_picture_url = EXCLUDED.profile_picture_url
        ''', (user_id, picture_url))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_user_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT profile_picture_url, name, email, is_admin FROM users WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        if row:
            return {'profile_picture_url': row[0], 'name': row[1], 'email': row[2], 'is_admin': row[3]}
        return None
    finally:
        cursor.close()
        conn.close()

def update_user_name(user_id, name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, name) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name
        ''', (user_id, name))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def delete_user_profile_picture(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET profile_picture_url = NULL WHERE user_id = %s', (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_id, email, password_hash, name, profile_picture_url, is_admin FROM users WHERE email = %s', (email,))
        row = cursor.fetchone()
        if row:
            return {'user_id': row[0], 'email': row[1], 'password_hash': row[2], 'name': row[3], 'profile_picture_url': row[4], 'is_admin': row[5]}
        return None
    finally:
        cursor.close()
        conn.close()

def create_native_user(user_id, email, password_hash, name, is_admin=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (user_id, email, password_hash, name, is_admin) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, email, password_hash, name, is_admin))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_or_create_google_user(google_sub, email, name, profile_picture_url):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if email:
            cursor.execute('SELECT user_id, is_admin FROM users WHERE email = %s', (email,))
            row = cursor.fetchone()
            if row:
                return row[0], row[1]
                
        cursor.execute('SELECT user_id, is_admin FROM users WHERE user_id = %s', (google_sub,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
            
        cursor.execute('''
            INSERT INTO users (user_id, email, name, profile_picture_url) 
            VALUES (%s, %s, %s, %s)
        ''', (google_sub, email, name, profile_picture_url))
        conn.commit()
        return google_sub, False
    finally:
        cursor.close()
        conn.close()

def log_search(user_id, query):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO search_history (user_id, query) VALUES (%s, %s)', (user_id, query))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_recent_searches(user_id, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT DISTINCT query FROM search_history WHERE user_id = %s ORDER BY query LIMIT %s', (user_id, limit))
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

def log_movie_view(user_id, movie_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO movie_views (user_id, movie_id) VALUES (%s, %s)', (user_id, movie_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def log_recommendation(user_id, rec_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO recommendation_logs (user_id, rec_type) VALUES (%s, %s)', (user_id, rec_type))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def check_is_admin(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        return row[0] if row else False
    finally:
        cursor.close()
        conn.close()

def get_admin_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM recommendation_logs')
        recs_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT movie_id, COUNT(*) as c FROM movie_views GROUP BY movie_id ORDER BY c DESC LIMIT 1')
        top_viewed = cursor.fetchone()
        
        cursor.execute('SELECT query, COUNT(*) as c FROM search_history GROUP BY query ORDER BY c DESC LIMIT 1')
        top_searched = cursor.fetchone()
        
        cursor.execute('SELECT rec_type, COUNT(*) as c FROM recommendation_logs GROUP BY rec_type')
        rec_types = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_users": users_count,
            "total_recommendations": recs_count,
            "most_viewed_movie_id": top_viewed[0] if top_viewed else None,
            "most_searched_query": top_searched[0] if top_searched else None,
            "recommendation_types": rec_types
        }
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
