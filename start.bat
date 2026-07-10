@echo off
echo Starting Hybrid Movie Recommender...

:: Start the FastAPI backend
start "Backend API" cmd /k "cd backend && venv\Scripts\uvicorn main:app --port 8000 --reload"

:: Wait for a couple of seconds to ensure backend is starting
timeout /t 3 /nobreak

:: Start the React frontend
start "Frontend App" cmd /k "cd frontend && npm run dev"

echo Both servers are starting in separate windows.
echo Frontend will be available at http://localhost:5173
echo Backend API is available at http://localhost:8000
