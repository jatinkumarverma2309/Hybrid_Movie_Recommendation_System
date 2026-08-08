# 🍿 MovieMatch: Hybrid Movie Recommendation System

MovieMatch is a state-of-the-art Movie Recommendation Engine and Web Application that understands both the structure of films and your unique tastes. It combines Content-Based Filtering, Collaborative Filtering, and an AI-powered Chatbot to deliver highly personalized movie suggestions.

## ✨ Features

* **Hybrid Recommendation Engine:**
  * **Content-Based Filtering:** Uses TF-IDF and Cosine Similarity to find structurally similar movies based on genres, cast, and overview.
  * **Collaborative Filtering:** Uses Singular Value Decomposition (SVD) trained on millions of user ratings to predict how much you will like a movie.
  * **Hybrid Mode:** Intelligently combines both algorithms for pinpoint accuracy.
* **Semantic AI Search:** Powered by Google's Gemini API, allowing you to search for movies using natural language (e.g., "Kids finding a treasure map").
* **User Authentication:** Supports both traditional Email/Password login (secured with bcrypt and JWT) and **Google OAuth**.
* **Personalized Profiles:** Users can manage Watchlists, Favorites, and custom profile pictures.
* **Admin Dashboard:** Real-time analytics, user statistics, and dynamic charts (powered by Recharts) showing genre distributions and platform usage.
* **Dynamic UI:** Beautiful, responsive frontend with a dark/light mode toggle.

## 🛠️ Tech Stack

**Frontend:**
* React (Vite)
* Lucide React (Icons)
* Recharts (Data Visualization)
* Axios (API Client)
* `@react-oauth/google` (Google Authentication)

**Backend:**
* FastAPI (High-performance API)
* Python (Pandas, NumPy, Scikit-Learn, Surprise)
* Google Generative AI (Gemini)
* SQLite (Database for user data, watchlists, etc.)
* JWT & Bcrypt (Security)
* RapidFuzz (Fuzzy string matching for searches)

## 🚀 Local Setup

### Prerequisites
* Node.js (v16+)
* Python (v3.9+)
* API Keys for [TMDB](https://www.themoviedb.org/) and [Google Gemini](https://aistudio.google.com/app/apikey).

### 1. Backend Setup
```bash
cd backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file and add your keys:
# TMDB_API_KEY=your_tmdb_key_here
# GEMINI_API_KEY=your_gemini_key_here

# Run the backend server
uvicorn main:app --reload
```
*Note: The backend depends on pre-trained ML models (`movies_df.pkl`, `svd_model.joblib`, etc.) which should be located in the `backend/models/` directory.*

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create a .env file and point to your backend:
# VITE_API_BASE_URL=http://localhost:8000

# Start the development server
npm run dev
```

## ☁️ Deployment Details

### Backend Deployment (e.g., Render, Railway)
1. **Host:** Deploy the `backend` folder as a Python web service.
2. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables:** Don't forget to add `TMDB_API_KEY` and `GEMINI_API_KEY`.
4. **Performance Note:** Because loading the ML models and dataframes into memory takes significant time, model initialization is deferred to a **background thread** upon startup. This ensures the app binds to its port immediately, avoiding cold-start timeouts and allowing authentication to work instantly while the recommendation engine warms up.

### Frontend Deployment (e.g., Vercel, Netlify)
1. **Host:** Deploy the `frontend` directory as a Vite/React app.
2. **Build Command:** `npm run build`
3. **Publish Directory:** `dist`
4. **Environment Variables:** Set `VITE_API_BASE_URL` to your live backend URL (e.g., `https://your-backend-app.onrender.com`).
5. **Google OAuth:** Ensure your deployed frontend URL (e.g., `https://moviematch.vercel.app`) is added to the **Authorized JavaScript Origins** in your Google Cloud Console for the Google Login to work.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.