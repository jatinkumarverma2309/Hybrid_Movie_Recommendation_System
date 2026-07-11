import os
import psycopg2
import uuid
from dotenv import load_dotenv

load_dotenv()
database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:MySQL123@localhost:5432/hybrid_movie_recommender')
conn = psycopg2.connect(database_url)
cur = conn.cursor()

# Delete if exists
cur.execute('DELETE FROM users WHERE email=%s', ('admin@moviematch.com',))

# Insert with hardcoded valid hash
user_id = str(uuid.uuid4().int)[:15]
hash_val = '$2b$12$TKniyyIleO6VpLRCxRDBoOpCXY4eFVAPcXiKMlXhb6GOOEuQQHT1C'

cur.execute('''
    INSERT INTO users (user_id, email, password_hash, name, is_admin) 
    VALUES (%s, %s, %s, %s, %s)
''', (user_id, 'admin@moviematch.com', hash_val, 'Super Admin', True))

conn.commit()
cur.close()
conn.close()
print("Admin created successfully.")
