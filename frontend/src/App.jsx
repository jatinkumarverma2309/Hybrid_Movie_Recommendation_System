import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Search, Film, Sparkles, Play, Heart, Bookmark, Compass, ArrowLeft, LogOut, Upload, Camera, UserCircle, X, Trash2, Edit2, Sun, Moon, BarChart2, Info, History, Clock } from 'lucide-react';
import { GoogleLogin, googleLogout } from '@react-oauth/google';
import { jwtDecode } from 'jwt-decode';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import './index.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const COLORS = ['#E50914', '#b81d24', '#ff4b4b', '#ff7b7b', '#ffaaaa', '#ffffff', '#cccccc', '#999999', '#666666', '#333333'];

const MovieCard = ({ movie, onClick, onToggleWatchlist, onToggleFavorite, isWatchlist, isFavorite }) => {
  return (
    <div className="movie-card" onClick={() => onClick(movie)}>
      {movie.poster_url ? (
        <img src={movie.poster_url} alt={movie.title} className="movie-poster" />
      ) : (
        <div className="movie-poster-fallback">
          <Film size={32} />
        </div>
      )}
      <div className="movie-card-overlay">
        <h4>{movie.title}</h4>
        <p>{movie.genres.replace(/\|/g, ' • ')}</p>
      </div>
      <div className="quick-actions" onClick={(e) => e.stopPropagation()}>
        <button 
          className={`action-btn ${isFavorite ? 'active-heart' : ''}`}
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(movie.movieId); }}
          title="Toggle Favorite"
        >
          <Heart size={16} fill={isFavorite ? "currentColor" : "none"} />
        </button>
        <button 
          className={`action-btn ${isWatchlist ? 'active-bookmark' : ''}`}
          onClick={(e) => { e.stopPropagation(); onToggleWatchlist(movie.movieId); }}
          title="Toggle Watchlist"
        >
          <Bookmark size={16} fill={isWatchlist ? "currentColor" : "none"} />
        </button>
      </div>
    </div>
  );
};

const MovieRow = ({ title, movies, onMovieClick, onToggleWatchlist, onToggleFavorite, watchlist, favorites }) => {
  if (!movies || movies.length === 0) return null;
  return (
    <div className="movie-row-container">
      <h2 className="row-title">{title}</h2>
      <div className="movie-row">
        {movies.map(movie => (
          <MovieCard 
            key={movie.movieId} 
            movie={movie} 
            onClick={onMovieClick}
            onToggleWatchlist={onToggleWatchlist}
            onToggleFavorite={onToggleFavorite}
            isWatchlist={watchlist.has(movie.movieId)}
            isFavorite={favorites.has(movie.movieId)}
          />
        ))}
      </div>
    </div>
  );
};

// ... ProfileView Code
const ProfileView = ({ user, customProfileUrl, setCustomProfileUrl, onUpdateName, profileData }) => {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editNameValue, setEditNameValue] = useState(user.name || '');
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('user_id', user.sub);
    formData.append('file', file);
    
    try {
      const res = await axios.post(`${API_BASE}/profile/picture`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCustomProfileUrl(res.data.profile_picture_url);
    } catch (err) {
      console.error('Error uploading file', err);
    }
  };

  const removePhoto = async () => {
    try {
      await axios.delete(`${API_BASE}/profile/${user.sub}/picture`);
      setCustomProfileUrl(null);
    } catch (err) {
      console.error('Error removing photo', err);
    }
  };

  const saveName = async () => {
    try {
      await axios.post(`${API_BASE}/profile/${user.sub}/name`, { name: editNameValue });
      onUpdateName(editNameValue);
      setIsEditingName(false);
    } catch (err) {
      console.error('Error updating name', err);
    }
  };

  const openCamera = async () => {
    setIsCameraOpen(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error('Camera access denied', err);
      setIsCameraOpen(false);
    }
  };

  const closeCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
    }
    setIsCameraOpen(false);
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const context = canvasRef.current.getContext('2d');
      canvasRef.current.width = videoRef.current.videoWidth;
      canvasRef.current.height = videoRef.current.videoHeight;
      context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);
      
      canvasRef.current.toBlob(async (blob) => {
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        const formData = new FormData();
        formData.append('user_id', user.sub);
        formData.append('file', file);
        
        try {
          const res = await axios.post(`${API_BASE}/profile/picture`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          setCustomProfileUrl(res.data.profile_picture_url);
          closeCamera();
        } catch (err) {
          console.error('Error uploading capture', err);
        }
      }, 'image/jpeg');
    }
  };

  const displayPic = customProfileUrl || user.picture;

  return (
    <div className="profile-container">
      <div className="profile-card">
        {displayPic ? (
          <img src={displayPic} alt="Profile" className="profile-picture-lg" />
        ) : (
          <div className="profile-picture-lg" style={{display:'flex', alignItems:'center', justifyContent:'center', background:'#333'}}>
            <UserCircle size={64} />
          </div>
        )}
        
        <div style={{ textAlign: 'center' }}>
          {isEditingName ? (
            <div className="name-edit-container">
              <input 
                className="name-input"
                value={editNameValue}
                onChange={e => setEditNameValue(e.target.value)}
                autoFocus
              />
              <button className="btn-primary" onClick={saveName} style={{padding: '0.5rem 1rem'}}>Save</button>
              <button className="btn-secondary" onClick={() => setIsEditingName(false)} style={{padding: '0.5rem 1rem'}}>Cancel</button>
            </div>
          ) : (
            <h2 style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
              {user.name} 
              <Edit2 size={16} style={{ cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setIsEditingName(true)} />
            </h2>
          )}
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>{user.email}</p>
          {profileData?.favourite_genre && (
            <p style={{ marginTop: '1rem', color: 'var(--accent)', fontWeight: '600' }}>
              Favourite Genre: {profileData.favourite_genre}
            </p>
          )}
        </div>
        
        <div className="profile-actions">
          <div className="upload-btn-wrapper">
            <button className="btn-secondary"><Upload size={20} /> Upload Photo</button>
            <input type="file" accept="image/*" onChange={handleFileUpload} />
          </div>
          <button className="btn-secondary" onClick={openCamera}><Camera size={20} /> Camera</button>
          {customProfileUrl && (
            <button className="btn-secondary" style={{ color: '#ef4444' }} onClick={removePhoto}>
              <Trash2 size={20} /> Remove Photo
            </button>
          )}
        </div>
      </div>

      {isCameraOpen && (
        <div className="camera-modal">
          <div className="camera-container">
            <h3>Capture Profile Picture</h3>
            <video ref={videoRef} autoPlay playsInline className="video-stream"></video>
            <canvas ref={canvasRef} style={{ display: 'none' }}></canvas>
            <div className="camera-actions" style={{ marginTop: '1rem' }}>
              <button className="btn-secondary" onClick={closeCamera}><X size={20} /> Cancel</button>
              <button className="btn-primary" onClick={capturePhoto}><Camera size={20} /> Capture</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const DashboardView = ({ user }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get(`${API_BASE}/analytics/dashboard?user_id=${user.sub}`);
        setData(res.data);
      } catch(err) {
        setError(err.response?.data?.detail || "Could not load analytics");
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [user.sub]);

  if (loading) return <div className="loader-container"><div className="loader"></div></div>;
  if (error) return <div className="error-msg">{error}</div>;

  const { stats, charts } = data;

  return (
    <div>
      <h2 className="section-title" style={{ marginBottom: '2rem' }}><BarChart2 size={24} color="var(--accent)" /> Admin Analytics</h2>
      
      <div className="dashboard-grid">
        <div className="metric-card">
          <h3>Total Users</h3>
          <div className="value">{stats.total_users}</div>
        </div>
        <div className="metric-card">
          <h3>Recommendations</h3>
          <div className="value">{stats.total_recommendations}</div>
        </div>
        <div className="metric-card">
          <h3>Most Viewed</h3>
          <div className="value" style={{ fontSize: '1.5rem', marginTop: '0.5rem' }}>{stats.most_viewed_movie_title}</div>
        </div>
        <div className="metric-card">
          <h3>Top Search</h3>
          <div className="value" style={{ fontSize: '1.5rem', marginTop: '0.5rem' }}>{stats.most_searched_query || 'N/A'}</div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-container">
          <h3>Genre Distribution</h3>
          <ResponsiveContainer width="100%" height="80%">
            <PieChart>
              <Pie data={charts.genres} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                {charts.genres.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: 'none', color: 'var(--text-primary)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        <div className="chart-container">
          <h3>Ratings Distribution</h3>
          <ResponsiveContainer width="100%" height="80%">
            <BarChart data={charts.ratings}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="rating" stroke="var(--text-secondary)" />
              <YAxis stroke="var(--text-secondary)" />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: 'none', color: 'var(--text-primary)' }} />
              <Bar dataKey="count" fill="var(--accent)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Top Actors</h3>
          <ResponsiveContainer width="100%" height="80%">
            <BarChart data={charts.actors} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" stroke="var(--text-secondary)" />
              <YAxis dataKey="name" type="category" width={150} stroke="var(--text-secondary)" />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: 'none', color: 'var(--text-primary)' }} />
              <Bar dataKey="count" fill="var(--accent)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h3>Recommendation Usage</h3>
          <ResponsiveContainer width="100%" height="80%">
            <PieChart>
              <Pie data={charts.recommendations} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                {charts.recommendations.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: 'none', color: 'var(--text-primary)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

const AboutView = () => (
  <div style={{ maxWidth: '800px', margin: '0 auto', lineHeight: '1.8' }}>
    <h1 style={{ fontSize: '3rem', marginBottom: '1.5rem', color: 'var(--accent)' }}>About MovieMatch</h1>
    <p style={{ fontSize: '1.2rem', marginBottom: '2rem', color: 'var(--text-secondary)' }}>
      MovieMatch is powered by a state-of-the-art Hybrid Recommendation Engine designed to understand both the structure of films and your unique tastes.
    </p>
    
    <div className="metric-card" style={{ marginBottom: '2rem' }}>
      <h2 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Content-Based Filtering</h2>
      <p style={{ color: 'var(--text-secondary)' }}>
        Using Term Frequency-Inverse Document Frequency (TF-IDF) alongside Cosine Similarity, we parse the genres, cast, and plots of over 20,000 movies. When you click "Similar", we instantly calculate the exact structural matches to that movie.
      </p>
    </div>

    <div className="metric-card" style={{ marginBottom: '2rem' }}>
      <h2 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Collaborative Filtering</h2>
      <p style={{ color: 'var(--text-secondary)' }}>
        Finding structurally similar movies is only half the battle. We use a powerful Singular Value Decomposition (SVD) algorithm trained on millions of ratings to predict exactly how many stars you would rate those recommendations, ensuring we only show the absolute best matches.
      </p>
    </div>
  </div>
);

const AdminSidebar = ({ currentView, setCurrentView, user, customProfileUrl, onLogout, toggleTheme, isLightMode }) => {
  const displayPic = customProfileUrl || user?.picture;
  
  return (
    <div className="sidebar">
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', marginBottom: '2rem', paddingLeft: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <div className="logo-mm" style={{ fontSize: '2.5rem', letterSpacing: '-3px', marginRight: '-3px' }}>MM</div>
          <div style={{ fontSize: '2rem', filter: 'drop-shadow(0 0 5px rgba(255, 223, 0, 0.4))' }}>🍿</div>
        </div>
        <div className="logo-text" style={{ fontSize: '0.7rem', letterSpacing: '4px', marginTop: '0', textShadow: 'none', color: 'var(--text-primary)' }}>Admin Portal</div>
      </div>
      
      <div className="user-profile" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '2rem', paddingLeft: '0.5rem' }}>
        {displayPic ? (
          <img src={displayPic} alt="Profile" style={{ width: '40px', height: '40px', objectFit: 'cover', borderRadius: '4px' }} />
        ) : (
          <UserCircle size={40} />
        )}
        <div style={{ overflow: 'hidden' }}>
          <div style={{ fontWeight: '600', fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.name} (Admin)</div>
        </div>
      </div>
      
      <nav className="nav-links">
        <button className={`nav-link ${currentView === 'dashboard' ? 'active' : ''}`} onClick={() => setCurrentView('dashboard')}>
          <BarChart2 size={20} /> Dashboard
        </button>
      </nav>
      
      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <button className="nav-link" onClick={toggleTheme}>
          {isLightMode ? <Moon size={20} /> : <Sun size={20} />} {isLightMode ? 'Dark Mode' : 'Light Mode'}
        </button>
        <button className="nav-link" onClick={onLogout} style={{ color: 'var(--text-secondary)' }}>
          <LogOut size={20} /> Sign Out
        </button>
      </div>
    </div>
  );
};

function AdminApp({ user, onLogout, toggleTheme, isLightMode }) {
  const [currentView, setCurrentView] = useState('dashboard');
  const [customProfileUrl, setCustomProfileUrl] = useState(user.picture || null);
  
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await axios.get(`${API_BASE}/profile/${user.sub}`);
        if (res.data.profile_picture_url) setCustomProfileUrl(res.data.profile_picture_url);
      } catch (err) {}
    };
    fetchProfile();
  }, [user.sub]);

  return (
    <div className="app-layout">
      <AdminSidebar currentView={currentView} setCurrentView={setCurrentView} user={user} customProfileUrl={customProfileUrl} onLogout={onLogout} toggleTheme={toggleTheme} isLightMode={isLightMode} />
      <main className="main-content">
        {currentView === 'dashboard' && <DashboardView user={user} />}
      </main>
    </div>
  );
}

const AIChatbot = ({ onMovieClick }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, type: 'bot', text: 'Hi! I am the MovieMatch AI. Describe a movie you want to watch and I will find it for you!', movies: [] }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    const userMsg = { id: Date.now(), type: 'user', text: input, movies: [] };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    
    try {
      const res = await axios.post(`${API_BASE}/chat`, { query: userMsg.text });
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        type: 'bot', 
        text: res.data.message, 
        movies: res.data.movies 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { id: Date.now() + 1, type: 'bot', text: 'Sorry, I encountered an error. Please try again.', movies: [] }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`chatbot-container ${isOpen ? 'open' : ''}`}>
      {!isOpen && (
        <button className="chatbot-toggle glow-effect" onClick={() => setIsOpen(true)}>
          <Sparkles size={24} />
        </button>
      )}
      
      {isOpen && (
        <div className="chatbot-window glow-effect">
          <div className="chatbot-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={20} color="var(--accent)" />
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>MovieMatch AI</h3>
            </div>
            <button className="close-btn" onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}>
              <X size={20} />
            </button>
          </div>
          
          <div className="chatbot-messages">
            {messages.map(msg => (
              <div key={msg.id} className={`chat-bubble-wrapper ${msg.type}`}>
                <div className="chat-bubble">
                  <p style={{ margin: 0 }}>{msg.text}</p>
                </div>
                {msg.movies && msg.movies.length > 0 && (
                  <div className="chat-movies">
                    {msg.movies.map(movie => (
                      <div key={movie.movieId} className="chat-movie-card" onClick={() => onMovieClick(movie)}>
                        {movie.poster_url ? (
                           <img src={movie.poster_url} alt={movie.title} />
                        ) : (
                           <div style={{width:'60px', height:'90px', background:'#222', display:'flex', alignItems:'center', justifyContent:'center'}}><Film size={20} color="#555"/></div>
                        )}
                        <div className="chat-movie-info">
                          <h5 style={{ margin: 0, fontSize: '0.85rem' }}>{movie.title}</h5>
                          <span style={{ fontSize: '0.7rem', color: '#888' }}>{movie.genres.split('|')[0]}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="chat-bubble-wrapper bot">
                <div className="chat-bubble typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          <form className="chatbot-input-area" onSubmit={handleSubmit}>
            <input 
              type="text" 
              placeholder="E.g., kids finding a treasure map..." 
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

function MainApp({ user: initialUser, onLogout, toggleTheme, isLightMode }) {
  const [user, setUser] = useState(initialUser);
  const USER_ID = user.sub;
  const [trendingMovies, setTrendingMovies] = useState([]);
  const [latestMovies, setLatestMovies] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [moodResults, setMoodResults] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [searchHistory, setSearchHistory] = useState([]);
  
  const [currentView, setCurrentView] = useState('discover'); 
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [extendedDetails, setExtendedDetails] = useState({});

  useEffect(() => {
    if (selectedMovie && selectedMovie.tmdbId) {
      setExtendedDetails({});
      axios.get(`${API_BASE}/movie/${selectedMovie.tmdbId}/details`)
        .then(res => setExtendedDetails(res.data))
        .catch(err => console.error(err));
    }
  }, [selectedMovie]);

  const [watchlist, setWatchlist] = useState(new Set());
  const [favorites, setFavorites] = useState(new Set());
  
  const [profileData, setProfileData] = useState(null);
  const [customProfileUrl, setCustomProfileUrl] = useState(user.picture || null);
  
  const [activeMood, setActiveMood] = useState(null);
  const [sortBy, setSortBy] = useState('default');

  useEffect(() => {
    fetchProfile();
    fetchLists();
    fetchSearchHistory();
    if (currentView === 'discover') {
      fetchDiscoverData();
    }
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await axios.get(`${API_BASE}/profile/${USER_ID}`);
      setProfileData(res.data);
      if (res.data.name) setUser(prev => ({ ...prev, name: res.data.name }));
      if (res.data.profile_picture_url) setCustomProfileUrl(res.data.profile_picture_url);
    } catch (err) {
      console.error("Error fetching profile", err);
    }
  };

  const fetchLists = async () => {
    try {
      const [wlRes, favRes] = await Promise.all([
        axios.get(`${API_BASE}/watchlist?user_id=${USER_ID}`),
        axios.get(`${API_BASE}/favorites?user_id=${USER_ID}`)
      ]);
      setWatchlist(new Set(wlRes.data.map(m => m.movieId)));
      setFavorites(new Set(favRes.data.map(m => m.movieId)));
    } catch (err) {
      console.error("Error fetching lists", err);
    }
  };
  
  const fetchSearchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE}/history/searches?user_id=${USER_ID}`);
      setSearchHistory(res.data);
    } catch(err) {}
  };

  const fetchDiscoverData = async () => {
    setLoading(true);
    setCurrentView('discover');
    setSelectedMovie(null);
    setActiveMood(null);
    try {
      const [popRes, latRes] = await Promise.all([
        axios.get(`${API_BASE}/movies/popular?limit=20`),
        axios.get(`${API_BASE}/movies/latest?limit=20`)
      ]);
      setTrendingMovies(popRes.data);
      setLatestMovies(latRes.data);
      setError(null);
    } catch (err) {
      setError('Could not connect to the recommendation API. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const executeSearch = async (query) => {
    setSearchQuery(query);
    setShowAutocomplete(false);
    if (!query.trim()) {
      fetchDiscoverData();
      return;
    }
    
    setLoading(true);
    setCurrentView('search');
    setSelectedMovie(null);
    try {
      // Log search
      await axios.post(`${API_BASE}/track/search`, { user_id: USER_ID, query });
      fetchSearchHistory(); // update history
      
      const res = await axios.get(`${API_BASE}/movies/search?q=${query}&limit=20`);
      setSearchResults(res.data);
      setSortBy('default');
      setError(null);
    } catch (err) {
      setError('Error searching movies.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    executeSearch(searchQuery);
  };

  const fetchMood = async (mood) => {
    setActiveMood(mood);
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/movies/mood?mood=${mood}&limit=20`);
      setMoodResults(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchListMovies = async (endpoint, viewName) => {
    setLoading(true);
    setCurrentView(viewName);
    setSelectedMovie(null);
    try {
      const res = await axios.get(`${API_BASE}/${endpoint}?user_id=${USER_ID}`);
      setSearchResults(res.data);
      setSortBy('default');
      setError(null);
    } catch (err) {
      setError(`Error fetching ${viewName}.`);
    } finally {
      setLoading(false);
    }
  };

  const handleMovieClick = async (movie) => {
    setSelectedMovie(movie);
    try {
      await axios.post(`${API_BASE}/track/view`, { user_id: USER_ID, movie_id: movie.movieId });
    } catch(err) {}
  };

  const toggleWatchlist = async (movieId) => {
    const isAdded = watchlist.has(movieId);
    const newSet = new Set(watchlist);
    if (isAdded) {
      newSet.delete(movieId);
      await axios.delete(`${API_BASE}/watchlist/${movieId}?user_id=${USER_ID}`);
      if (currentView === 'watchlist') setSearchResults(searchResults.filter(m => m.movieId !== movieId));
    } else {
      newSet.add(movieId);
      await axios.post(`${API_BASE}/watchlist/${movieId}?user_id=${USER_ID}`);
    }
    setWatchlist(newSet);
  };

  const toggleFavorite = async (movieId) => {
    const isAdded = favorites.has(movieId);
    const newSet = new Set(favorites);
    if (isAdded) {
      newSet.delete(movieId);
      await axios.delete(`${API_BASE}/favorites/${movieId}?user_id=${USER_ID}`);
      if (currentView === 'favorites') setSearchResults(searchResults.filter(m => m.movieId !== movieId));
    } else {
      newSet.add(movieId);
      await axios.post(`${API_BASE}/favorites/${movieId}?user_id=${USER_ID}`);
    }
    setFavorites(newSet);
  };

  const getRecommendations = async (movie) => {
    setLoading(true);
    setCurrentView('search');
    setSelectedMovie(null);
    setSearchQuery('');
    try {
      await axios.post(`${API_BASE}/track/recommend`, { user_id: USER_ID, rec_type: 'hybrid' });
      const res = await axios.get(`${API_BASE}/recommend/hybrid?user_id=${USER_ID}&movie_id=${movie.movieId}&limit=20`);
      setSearchResults(res.data);
      setSortBy('default');
      setError(null);
    } catch (err) {
      setError('Error fetching recommendations.');
    } finally {
      setLoading(false);
    }
  };

  const getSortedResults = (list) => {
    if (sortBy === 'alphabetical') {
      return [...list].sort((a,b) => a.title.localeCompare(b.title));
    } else if (sortBy === 'latest') {
      return [...list].sort((a,b) => {
        const yA = parseInt(a.title.match(/\((\d{4})\)/)?.[1] || 0);
        const yB = parseInt(b.title.match(/\((\d{4})\)/)?.[1] || 0);
        return yB - yA;
      });
    }
    return list;
  };

  // Movie Details View
  if (selectedMovie) {
    const isWl = watchlist.has(selectedMovie.movieId);
    const isFav = favorites.has(selectedMovie.movieId);
    
    let embedUrl = null;
    if (selectedMovie.trailer_url && selectedMovie.trailer_url.includes('youtube.com/watch?v=')) {
      const videoId = selectedMovie.trailer_url.split('v=')[1];
      embedUrl = `https://www.youtube.com/embed/${videoId}`;
    }
    
    return (
      <div className="app-layout">
        <Sidebar currentView={currentView} setCurrentView={setCurrentView} onDiscover={fetchDiscoverData} onWatchlist={() => fetchListMovies('watchlist', 'watchlist')} onFavorites={() => fetchListMovies('favorites', 'favorites')} user={user} customProfileUrl={customProfileUrl} profileData={profileData} onLogout={onLogout} toggleTheme={toggleTheme} isLightMode={isLightMode} />
        
        <main className="main-content details-page">
          <button className="back-btn" onClick={() => setSelectedMovie(null)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '2rem' }}>
            <ArrowLeft size={20} /> Back
          </button>
          
          <div className="details-header">
            {selectedMovie.poster_url ? (
               <img src={selectedMovie.poster_url} alt={selectedMovie.title} className="details-poster" />
            ) : (
               <div className="details-poster movie-poster-fallback">
                 <Film size={48} />
               </div>
            )}
            <div className="details-info">
              <h1 className="details-title">{selectedMovie.title}</h1>
              <div className="details-meta">
                <span>{selectedMovie.genres.replace(/\|/g, ' • ')}</span>
                {extendedDetails.runtime && (
                  <>
                    <span style={{ margin: '0 8px', color: 'var(--text-secondary)' }}>•</span>
                    <span>⏳ {extendedDetails.runtime} min</span>
                  </>
                )}
                {extendedDetails.vote_average && (
                  <>
                    <span style={{ margin: '0 8px', color: 'var(--text-secondary)' }}>•</span>
                    <span>⭐ {extendedDetails.vote_average.toFixed(1)}/10</span>
                  </>
                )}
              </div>
              
              <p className="details-overview">{selectedMovie.overview || "No overview available."}</p>
              
              <div className="details-cast">
                <h3>Top Cast</h3>
                <p>{selectedMovie.cast || "Unknown"}</p>
              </div>
              
              <div className="details-actions">
                <button 
                  className="btn-primary" 
                  onClick={() => toggleFavorite(selectedMovie.movieId)}
                >
                  <Heart size={20} fill={isFav ? "white" : "none"} color={isFav ? "white" : "black"} /> 
                  {isFav ? 'Favorited' : 'Favorite'}
                </button>
                <button 
                  className="btn-secondary" 
                  onClick={() => toggleWatchlist(selectedMovie.movieId)}
                >
                  <Bookmark size={20} fill={isWl ? "white" : "none"} /> 
                  {isWl ? 'In Watchlist' : 'Watchlist'}
                </button>
                <button 
                  className="btn-secondary" 
                  onClick={() => getRecommendations(selectedMovie)}
                >
                  <Sparkles size={20} /> Similar
                </button>
              </div>
            </div>
          </div>
          
          {embedUrl && (
            <div className="trailer-section" style={{ marginTop: '3rem' }}>
              <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Play size={24} color="var(--accent)" /> Trailer</h2>
              <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, overflow: 'hidden', borderRadius: '8px', background: '#000' }}>
                <iframe 
                  style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
                  src={embedUrl} 
                  title="YouTube video player" 
                  frameBorder="0" 
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                  allowFullScreen
                ></iframe>
              </div>
            </div>
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar currentView={currentView} setCurrentView={setCurrentView} onDiscover={fetchDiscoverData} onWatchlist={() => fetchListMovies('watchlist', 'watchlist')} onFavorites={() => fetchListMovies('favorites', 'favorites')} user={user} customProfileUrl={customProfileUrl} profileData={profileData} onLogout={onLogout} toggleTheme={toggleTheme} isLightMode={isLightMode} />
      
      <main className="main-content">
        <header>
          <div className="search-container" style={{ position: 'relative' }}>
            <form onSubmit={handleSearchSubmit}>
              <Search className="search-icon" size={20} />
              <input 
                type="text" 
                className="search-input"
                placeholder="Titles, people, genres" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setShowAutocomplete(true)}
                onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
              />
            </form>
            {showAutocomplete && searchHistory.length > 0 && (
              <div className="search-autocomplete">
                {searchHistory.map((h, i) => (
                  <div key={i} className="autocomplete-item" onClick={() => executeSearch(h)}>
                    <Clock size={16} color="var(--text-secondary)"/> {h}
                  </div>
                ))}
              </div>
            )}
          </div>
        </header>

        {error && <div className="error-msg">{error}</div>}
        
        {currentView === 'profile' ? (
          <ProfileView 
            user={user} 
            customProfileUrl={customProfileUrl} 
            setCustomProfileUrl={setCustomProfileUrl} 
            onUpdateName={(name) => setUser({...user, name})}
            profileData={profileData}
          />
        ) : currentView === 'dashboard' ? (
          <DashboardView user={user} />
        ) : currentView === 'about' ? (
          <AboutView />
        ) : loading ? (
          <div className="loader-container">
            <div className="loader"></div>
          </div>
        ) : currentView === 'discover' ? (
          <>
            <div className="mood-selector">
              <span style={{ display: 'flex', alignItems: 'center', fontWeight: '600', marginRight: '1rem' }}>Mood:</span>
              {['Happy', 'Thrilling', 'Scary', 'Romantic', 'Sad', 'Adventurous'].map(mood => (
                <button 
                  key={mood} 
                  className={`mood-btn ${activeMood === mood ? 'active' : ''}`}
                  onClick={() => fetchMood(mood)}
                >
                  {mood}
                </button>
              ))}
            </div>
            
            {activeMood ? (
              <MovieRow title={`${activeMood} Movies`} movies={moodResults} onMovieClick={handleMovieClick} onToggleWatchlist={toggleWatchlist} onToggleFavorite={toggleFavorite} watchlist={watchlist} favorites={favorites} />
            ) : (
              <>
                <MovieRow title="Trending Now" movies={trendingMovies} onMovieClick={handleMovieClick} onToggleWatchlist={toggleWatchlist} onToggleFavorite={toggleFavorite} watchlist={watchlist} favorites={favorites} />
                <MovieRow title="Latest Releases" movies={latestMovies} onMovieClick={handleMovieClick} onToggleWatchlist={toggleWatchlist} onToggleFavorite={toggleFavorite} watchlist={watchlist} favorites={favorites} />
              </>
            )}
          </>
        ) : (
          <div className="movie-row-container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 className="row-title" style={{ marginBottom: 0 }}>
                {currentView === 'search' && 'Search Results'}
                {currentView === 'watchlist' && 'My List'}
                {currentView === 'favorites' && 'Favorites'}
              </h2>
              <select className="sort-select" value={sortBy} onChange={e => setSortBy(e.target.value)}>
                <option value="default">Sort: Default</option>
                <option value="alphabetical">Alphabetical (A-Z)</option>
                <option value="latest">Latest Release</option>
              </select>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' }}>
              {getSortedResults(searchResults).map(movie => (
                <MovieCard 
                  key={movie.movieId} 
                  movie={movie} 
                  onClick={handleMovieClick}
                  onToggleWatchlist={toggleWatchlist}
                  onToggleFavorite={toggleFavorite}
                  isWatchlist={watchlist.has(movie.movieId)}
                  isFavorite={favorites.has(movie.movieId)}
                />
              ))}
            </div>
            {searchResults.length === 0 && <p style={{color: 'var(--text-secondary)', paddingLeft: '0.5rem'}}>No movies found.</p>}
          </div>
        )}
      </main>
      <AIChatbot onMovieClick={handleMovieClick} />
    </div>
  );
}

const Sidebar = ({ currentView, setCurrentView, onDiscover, onWatchlist, onFavorites, user, customProfileUrl, profileData, onLogout, toggleTheme, isLightMode }) => {
  const displayPic = customProfileUrl || user?.picture;
  
  return (
    <div className="sidebar">
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', marginBottom: '2rem', paddingLeft: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <div className="logo-mm" style={{ fontSize: '2.5rem', letterSpacing: '-3px', marginRight: '-3px' }}>MM</div>
          <div style={{ fontSize: '2rem', filter: 'drop-shadow(0 0 5px rgba(255, 223, 0, 0.4))' }}>🍿</div>
        </div>
        <div className="logo-text" style={{ fontSize: '0.7rem', letterSpacing: '4px', marginTop: '0', textShadow: 'none', color: 'var(--text-primary)' }}>MovieMatch</div>
      </div>
      
      <div className="user-profile" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '2rem', paddingLeft: '0.5rem' }}>
        {displayPic ? (
          <img src={displayPic} alt="Profile" style={{ width: '40px', height: '40px', objectFit: 'cover', borderRadius: '4px' }} />
        ) : (
          <UserCircle size={40} />
        )}
        <div style={{ overflow: 'hidden' }}>
          <div style={{ fontWeight: '600', fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user?.name}</div>
        </div>
      </div>
      
      <nav className="nav-links">
        <button className={`nav-link ${currentView === 'discover' || currentView === 'search' ? 'active' : ''}`} onClick={onDiscover}>
          <Compass size={20} /> Discover
        </button>
        <button className={`nav-link ${currentView === 'watchlist' ? 'active' : ''}`} onClick={onWatchlist}>
          <Bookmark size={20} /> My List
        </button>
        <button className={`nav-link ${currentView === 'favorites' ? 'active' : ''}`} onClick={onFavorites}>
          <Heart size={20} /> Favorites
        </button>
        <button className={`nav-link ${currentView === 'profile' ? 'active' : ''}`} onClick={() => setCurrentView('profile')}>
          <UserCircle size={20} /> Profile
        </button>
        <button className={`nav-link ${currentView === 'about' ? 'active' : ''}`} onClick={() => setCurrentView('about')}>
          <Info size={20} /> About Engine
        </button>
      </nav>
      
      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <button className="nav-link" onClick={toggleTheme}>
          {isLightMode ? <Moon size={20} /> : <Sun size={20} />} {isLightMode ? 'Dark Mode' : 'Light Mode'}
        </button>
        <button className="nav-link" onClick={onLogout} style={{ color: 'var(--text-secondary)' }}>
          <LogOut size={20} /> Sign Out
        </button>
      </div>
    </div>
  );
};

function App() {
  const [user, setUser] = useState(null);
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [isAdminPortal, setIsAdminPortal] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [authError, setAuthError] = useState('');
  
  const [isLightMode, setIsLightMode] = useState(false);

  useEffect(() => {
    if (isLightMode) {
      document.body.classList.add('light');
    } else {
      document.body.classList.remove('light');
    }
  }, [isLightMode]);

  const handleNativeAuth = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      const endpoint = isLoginMode ? '/auth/login' : '/auth/register';
      const payload = isLoginMode ? { email, password } : { name, email, password };
      const res = await axios.post(`${API_BASE}${endpoint}`, payload);
      
      if (isAdminPortal && !res.data.user.is_admin) {
        setAuthError('Unauthorized: Admin access only');
        return;
      }
      
      const decoded = jwtDecode(res.data.token);
      // We pass the is_admin flag from the response payload directly to user state so AdminApp renders immediately
      setUser({ ...decoded, is_admin: res.data.user.is_admin });
    } catch (err) {
      setAuthError(err.response?.data?.detail || 'Authentication failed');
    }
  };

  if (!user) {
    return (
      <div className="login-page">
        <div className="login-box glow-effect">
          
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border)', paddingBottom: '1rem' }}>
             <button onClick={() => {setIsAdminPortal(false); setAuthError('');}} className="nav-link" style={{ width: 'auto', background: !isAdminPortal ? 'rgba(229, 9, 20, 0.2)' : 'transparent', color: !isAdminPortal ? 'white' : 'gray', border: !isAdminPortal ? '1px solid var(--accent)' : 'none', padding: '0.5rem 1.5rem', margin: '0 0.5rem' }}>User Portal</button>
             <button onClick={() => {setIsAdminPortal(true); setAuthError('');}} className="nav-link" style={{ width: 'auto', background: isAdminPortal ? 'rgba(229, 9, 20, 0.2)' : 'transparent', color: isAdminPortal ? 'white' : 'gray', border: isAdminPortal ? '1px solid var(--accent)' : 'none', padding: '0.5rem 1.5rem', margin: '0 0.5rem' }}>Admin Portal</button>
          </div>

          <div className="logo-container">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div className="logo-mm">MM</div>
              <div style={{ fontSize: '4rem', filter: 'drop-shadow(0 0 10px rgba(255, 223, 0, 0.4))' }}>🍿</div>
            </div>
            <h1 className="logo-text">{isAdminPortal ? 'Admin Portal' : 'MovieMatch'}</h1>
          </div>
          <h2 style={{ textAlign: 'center' }}>{isLoginMode ? 'Sign In' : 'Sign Up'}</h2>
          
          {authError && <div className="error-msg">{authError}</div>}
          
          <form onSubmit={handleNativeAuth} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {!isLoginMode && (
              <input 
                type="text" 
                className="login-input" 
                placeholder="Full Name" 
                value={name}
                onChange={e => setName(e.target.value)}
                required
              />
            )}
            <input 
              type="email" 
              className="login-input" 
              placeholder="Email address" 
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <input 
              type="password" 
              className="login-input" 
              placeholder="Password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <button type="submit" className="login-btn">
              {isLoginMode ? 'Sign In' : 'Sign Up'}
            </button>
          </form>

          {!isAdminPortal && (
            <>
              <div className="divider">OR</div>

              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <GoogleLogin
                  onSuccess={async (credentialResponse) => {
                    try {
                      const res = await axios.post(`${API_BASE}/auth/verify`, { token: credentialResponse.credential });
                      // Note: Google users currently default to non-admin, so this bypasses admin check. 
                      // This is fine since it's hidden during Admin Portal login.
                      setUser({ ...jwtDecode(credentialResponse.credential), is_admin: res.data.is_admin });
                    } catch(err) {
                      setAuthError('Google sign in failed');
                    }
                  }}
                  onError={() => {
                    setAuthError('Google sign in failed');
                  }}
                  theme="filled_black"
                />
              </div>
            </>
          )}

          <div className="login-toggle">
            {isLoginMode ? 'New to MovieMatch?' : 'Already have an account?'}
            <span onClick={() => setIsLoginMode(!isLoginMode)}>
              {isLoginMode ? 'Sign up now.' : 'Sign in.'}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Route entirely to AdminApp if logged into Admin Portal (or if user is admin and specifically wants Admin portal)
  // Actually, if they are verified as admin and isAdminPortal was checked, route to AdminApp
  if (isAdminPortal && user.is_admin) {
    return <AdminApp user={user} onLogout={() => { googleLogout(); setUser(null); }} toggleTheme={() => setIsLightMode(!isLightMode)} isLightMode={isLightMode} />;
  }

  return <MainApp user={user} onLogout={() => { googleLogout(); setUser(null); }} toggleTheme={() => setIsLightMode(!isLightMode)} isLightMode={isLightMode} />;
}

export default App;
