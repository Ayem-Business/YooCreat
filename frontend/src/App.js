import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { FaBook, FaSignOutAlt, FaPlus, FaSpinner, FaCheckCircle, FaEye, FaGoogle } from 'react-icons/fa';
import './App.css';
import { ToastProvider, useToast } from './ToastContext';

// Configuration API URL intelligente pour dev et production
// Dev (localhost): http://localhost:8001
// Prod (Emergent): même domaine, requêtes /api/* proxiées automatiquement
const getAPIUrl = () => {
  // Si variable d'environnement explicite, l'utiliser
  if (process.env.REACT_APP_BACKEND_URL) {
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  // Sinon, détection automatique
  if (window.location.hostname === 'localhost') {
    return 'http://localhost:8001';
  }
  
  // Production: utiliser le même domaine (proxy Kubernetes)
  return window.location.origin;
};

const API_URL = getAPIUrl();

// Configure axios to send cookies with all requests
axios.defaults.withCredentials = true;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [processingOAuth, setProcessingOAuth] = useState(false);

  // Check for OAuth session_id in URL fragment
  useEffect(() => {
    const processOAuthCallback = async () => {
      const hash = window.location.hash;
      const params = new URLSearchParams(hash.substring(1));
      const sessionId = params.get('session_id');

      if (sessionId && !processingOAuth) {
        setProcessingOAuth(true);
        setLoading(true);

        try {
          // Exchange session_id for user data
          const response = await axios.post(`${API_URL}/api/auth/google`, {
            session_id: sessionId
          }, {
            withCredentials: true // Enable cookies
          });

          // Clean URL
          window.history.replaceState({}, document.title, window.location.pathname);

          // Set user data
          setUser(response.data.user);
          setToken(response.data.session_token);
          
          // No need to set Authorization header for cookie-based auth
          // But keep it for backward compatibility with JWT
          if (response.data.session_token) {
            axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.session_token}`;
          }
        } catch (error) {
          console.error('OAuth error:', error);
          alert('Erreur lors de la connexion avec Google. Veuillez réessayer.');
        } finally {
          setLoading(false);
          setProcessingOAuth(false);
        }
      }
    };

    processOAuthCallback();
  }, [processingOAuth]);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/auth/me`, {
          withCredentials: true
        });
        setUser(response.data);
      } catch (error) {
        logout();
      } finally {
        setLoading(false);
      }
    };

    // Don't fetch if we're processing OAuth
    if (!processingOAuth) {
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        fetchUser();
      } else {
        // Try to fetch with cookie only
        fetchUser();
      }
    }
  }, [token, processingOAuth]);

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    setToken(token);
    setUser(userData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API_URL}/api/auth/logout`, {}, {
        withCredentials: true
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => useContext(AuthContext);

// Login/Register Component
const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useAuth();
  const navigate = useNavigate();

  // Redirection automatique si utilisateur déjà connecté (après OAuth ou login normal)
  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
      const response = await axios.post(`${API_URL}${endpoint}`, formData);
      
      login(response.data.token, response.data.user);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Une erreur est survenue');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // Redirect to Emergent OAuth with redirect back to root
    // L'utilisateur reviendra sur la page de connexion avec #session_id
    // qui sera automatiquement traité par AuthProvider
    const redirectUrl = `${window.location.origin}/`;
    const authUrl = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    window.location.href = authUrl;
  };

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <div className="card max-w-md w-full">
        <div className="text-center mb-8">
          <FaBook className="text-6xl text-primary-violet mx-auto mb-4" />
          <h1 className="text-4xl font-bold text-gray-800 mb-2">YooCreat</h1>
          <p className="text-gray-600">Créez des ebooks professionnels avec l'IA</p>
        </div>

        <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setIsLogin(true)}
            className={`flex-1 py-2 rounded-md font-semibold transition-all ${
              isLogin ? 'bg-white shadow text-primary-blue' : 'text-gray-600'
            }`}
            data-testid="login-tab"
          >
            Connexion
          </button>
          <button
            onClick={() => setIsLogin(false)}
            className={`flex-1 py-2 rounded-md font-semibold transition-all ${
              !isLogin ? 'bg-white shadow text-primary-blue' : 'text-gray-600'
            }`}
            data-testid="register-tab"
          >
            Inscription
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="label">Nom d'utilisateur</label>
              <input
                type="text"
                className="input-field"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required={!isLogin}
                data-testid="username-input"
              />
            </div>
          )}

          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input-field"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              data-testid="email-input"
            />
          </div>

          <div>
            <label className="label">Mot de passe</label>
            <input
              type="password"
              className="input-field"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              data-testid="password-input"
            />
          </div>

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded" data-testid="error-message">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center"
            data-testid="submit-button"
          >
            {loading ? <FaSpinner className="animate-spin mr-2" /> : null}
            {isLogin ? 'Se connecter' : 'S\'inscrire'}
          </button>
        </form>

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Ou</span>
            </div>
          </div>

          <button
            onClick={handleGoogleLogin}
            className="mt-4 w-full flex items-center justify-center px-6 py-3 border-2 border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-all"
            data-testid="google-login-button"
          >
            <FaGoogle className="mr-2 text-red-500" />
            Continuer avec Google
          </button>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const [ebooks, setEbooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchEbooks();
  }, []);

  const fetchEbooks = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/ebooks/list`);
      setEbooks(response.data.ebooks);
    } catch (error) {
      console.error('Error fetching ebooks:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="gradient-bg text-white p-4 shadow-lg">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <FaBook className="text-3xl" />
            <h1 className="text-2xl font-bold">YooCreat</h1>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">Bonjour, {user?.username}</span>
            <button
              onClick={logout}
              className="flex items-center space-x-2 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-all"
              data-testid="logout-button"
            >
              <FaSignOutAlt />
              <span>Déconnexion</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="container mx-auto p-8">
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-3xl font-bold text-gray-800">Mes Ebooks</h2>
          <button
            onClick={() => navigate('/create')}
            className="btn-primary flex items-center space-x-2"
            data-testid="create-ebook-button"
          >
            <FaPlus />
            <span>Créer un Ebook</span>
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="spinner"></div>
          </div>
        ) : ebooks.length === 0 ? (
          <div className="card text-center py-16">
            <FaBook className="text-6xl text-gray-300 mx-auto mb-4" />
            <h3 className="text-2xl font-semibold text-gray-600 mb-2">Aucun ebook pour l'instant</h3>
            <p className="text-gray-500 mb-6">Commencez par créer votre premier ebook avec l'IA</p>
            <button
              onClick={() => navigate('/create')}
              className="btn-primary inline-flex items-center space-x-2"
            >
              <FaPlus />
              <span>Créer mon premier Ebook</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {ebooks.map((ebook) => (
              <div
                key={ebook._id}
                className="ebook-card"
                onClick={() => navigate(`/ebook/${ebook._id}`)}
                data-testid={`ebook-card-${ebook._id}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <FaBook className="text-4xl text-primary-violet" />
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    ebook.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {ebook.status === 'completed' ? 'Terminé' : 'Brouillon'}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-2">{ebook.title}</h3>
                <p className="text-sm text-gray-600 mb-2">Par {ebook.author}</p>
                <p className="text-sm text-gray-500 mb-4 line-clamp-2">{ebook.description}</p>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>{ebook.chapters_count} chapitres</span>
                  <span>{ebook.length}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Ebook Creator Component
const EbookCreator = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Form, 2: TOC Preview, 3: Generation
  const [formData, setFormData] = useState({
    author: '',
    title: '',
    tone: 'Professionnel',
    target_audience: [],
    description: '',
    chapters_count: 5,
    length: 'Moyen: 20-50 pages',
    genre: 'Guide pratique',
    about_author: '',
    acknowledgments: '',
    preface: ''
  });
  const [formStep, setFormStep] = useState(1); // Sub-step for form (1 or 2)
  const [toc, setToc] = useState([]);
  const [ebookId, setEbookId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generatingContent, setGeneratingContent] = useState(false);
  const [generatedChapters, setGeneratedChapters] = useState([]);
  const [error, setError] = useState('');

  const tones = ['Professionnel', 'Conversationnel', 'Académique', 'Humoristique', 'Inspirant', 'Technique', 'Storytelling'];
  const audiences = ['Enfants', 'Adolescents', 'Adultes', 'Professionnels', 'Seniors', 'Débutants', 'Experts'];
  const genres = ['Roman', 'Essai', 'Guide pratique', 'Autobiographie', 'Poésie', 'Manuel', 'Développement personnel', 'Business', 'Science', 'Autre'];
  const lengths = ['Court: 5-10 pages', 'Moyen: 20-50 pages', 'Long: 50-100 pages', 'Très long: 100+ pages'];

  const handleAudienceToggle = (audience) => {
    if (formData.target_audience.includes(audience)) {
      setFormData({
        ...formData,
        target_audience: formData.target_audience.filter(a => a !== audience)
      });
    } else {
      setFormData({
        ...formData,
        target_audience: [...formData.target_audience, audience]
      });
    }
  };

  const handleGenerateTOC = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Create ebook first
      const createResponse = await axios.post(`${API_URL}/api/ebooks/create`, formData);
      setEbookId(createResponse.data.ebook_id);

      // Generate TOC
      const tocResponse = await axios.post(`${API_URL}/api/ebooks/generate-toc`, formData);
      setToc(tocResponse.data.toc);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la génération de la table des matières');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateContent = async () => {
    setError('');
    setGeneratingContent(true);

    try {
      // Save TOC first
      await axios.post(`${API_URL}/api/ebooks/${ebookId}/save-toc`, { toc });

      // Generate content
      const response = await axios.post(`${API_URL}/api/ebooks/generate-content`, {
        ebook_id: ebookId,
        toc: toc
      });

      setGeneratedChapters(response.data.chapters);
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la génération du contenu');
    } finally {
      setGeneratingContent(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="gradient-bg text-white p-4 shadow-lg">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <FaBook className="text-3xl" />
            <h1 className="text-2xl font-bold">YooCreat</h1>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-all"
            data-testid="back-to-dashboard-button"
          >
            ← Retour au Dashboard
          </button>
        </div>
      </nav>

      <div className="container mx-auto p-8 max-w-4xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8">
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 ${step >= 1 ? 'text-primary-blue' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                step >= 1 ? 'bg-primary-blue text-white' : 'bg-gray-300'
              }`}>1</div>
              <span className="font-semibold">Informations</span>
            </div>
            <div className="w-16 h-1 bg-gray-300"></div>
            <div className={`flex items-center space-x-2 ${step >= 2 ? 'text-primary-violet' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                step >= 2 ? 'bg-primary-violet text-white' : 'bg-gray-300'
              }`}>2</div>
              <span className="font-semibold">Table des matières</span>
            </div>
            <div className="w-16 h-1 bg-gray-300"></div>
            <div className={`flex items-center space-x-2 ${step >= 3 ? 'text-primary-orange' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                step >= 3 ? 'bg-primary-orange text-white' : 'bg-gray-300'
              }`}>3</div>
              <span className="font-semibold">Génération</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6" data-testid="error-message">
            {error}
          </div>
        )}

        {/* Step 1: Form */}
        {step === 1 && (
          <div className="card">
            <h2 className="text-3xl font-bold text-gray-800 mb-6">Créer un nouvel Ebook</h2>
            
            {/* Sub-steps indicator */}
            <div className="flex items-center justify-center mb-6 space-x-4">
              <button
                type="button"
                onClick={() => setFormStep(1)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                  formStep === 1 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600'
                }`}
              >
                Étape 1 : Informations principales
              </button>
              <button
                type="button"
                onClick={() => setFormStep(2)}
                className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                  formStep === 2 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600'
                }`}
              >
                Étape 2 : Remerciements & Préface
              </button>
            </div>

            <form onSubmit={handleGenerateTOC} className="space-y-6">
              {/* Form Step 1: Main Information */}
              {formStep === 1 && (
                <>
                  <div>
                    <label className="label">Nom de l'auteur</label>
                    <input
                      type="text"
                      className="input-field"
                      value={formData.author}
                      onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                      required
                      data-testid="author-input"
                    />
                  </div>

                  <div>
                    <label className="label">Titre du livre</label>
                    <input
                      type="text"
                      className="input-field"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      required
                      data-testid="title-input"
                    />
                  </div>

                  <div>
                    <label className="label">Genre du livre</label>
                    <select
                      className="select-field"
                      value={formData.genre}
                      onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                      data-testid="genre-select"
                    >
                      {genres.map(genre => (
                        <option key={genre} value={genre}>{genre}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="label">Ton</label>
                    <select
                      className="select-field"
                      value={formData.tone}
                      onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
                      data-testid="tone-select"
                    >
                      {tones.map(tone => (
                        <option key={tone} value={tone}>{tone}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="label">Public cible (sélection multiple)</label>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {audiences.map(audience => (
                        <button
                          key={audience}
                          type="button"
                          onClick={() => handleAudienceToggle(audience)}
                          className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                            formData.target_audience.includes(audience)
                              ? 'bg-primary-violet text-white'
                              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                          }`}
                          data-testid={`audience-${audience.toLowerCase()}`}
                        >
                          {audience}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="label">Description du livre</label>
                    <textarea
                      className="input-field"
                      rows="5"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      placeholder="Décrivez le contenu souhaité, les thèmes principaux, et les objectifs du livre..."
                      required
                      data-testid="description-input"
                    ></textarea>
                  </div>

                  <div>
                    <label className="label">À propos de l'auteur (optionnel)</label>
                    <textarea
                      className="input-field"
                      rows="3"
                      value={formData.about_author}
                      onChange={(e) => setFormData({ ...formData, about_author: e.target.value })}
                      placeholder="Biographie courte de l'auteur, expérience, qualifications..."
                      data-testid="about-author-input"
                    ></textarea>
                  </div>

                  <div>
                    <label className="label">Nombre de chapitres: {formData.chapters_count}</label>
                    <input
                      type="range"
                      min="1"
                      max="50"
                      className="w-full"
                      value={formData.chapters_count}
                      onChange={(e) => setFormData({ ...formData, chapters_count: parseInt(e.target.value) })}
                      data-testid="chapters-count-slider"
                    />
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>1</span>
                      <span>25</span>
                      <span>50</span>
                    </div>
                  </div>

                  <div>
                    <label className="label">Longueur approximative</label>
                    <select
                      className="select-field"
                      value={formData.length}
                      onChange={(e) => setFormData({ ...formData, length: e.target.value })}
                      data-testid="length-select"
                    >
                      {lengths.map(length => (
                        <option key={length} value={length}>{length}</option>
                      ))}
                    </select>
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => setFormStep(2)}
                      className="bg-blue-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-600"
                    >
                      Suivant : Remerciements & Préface →
                    </button>
                  </div>
                </>
              )}

              {/* Form Step 2: Acknowledgments & Preface */}
              {formStep === 2 && (
                <>
                  <div>
                    <label className="label">Remerciements (optionnel)</label>
                    <textarea
                      className="input-field"
                      rows="5"
                      value={formData.acknowledgments}
                      onChange={(e) => setFormData({ ...formData, acknowledgments: e.target.value })}
                      placeholder="Dédicaces, remerciements aux personnes qui ont contribué..."
                      data-testid="acknowledgments-input"
                    ></textarea>
                    <p className="text-sm text-gray-500 mt-1">
                      Ex: Je remercie ma famille pour leur soutien...
                    </p>
                  </div>

                  <div>
                    <label className="label">Préface / Avant-propos (optionnel)</label>
                    <textarea
                      className="input-field"
                      rows="7"
                      value={formData.preface}
                      onChange={(e) => setFormData({ ...formData, preface: e.target.value })}
                      placeholder="Introduction au livre, contexte, motivations de l'auteur..."
                      data-testid="preface-input"
                    ></textarea>
                    <p className="text-sm text-gray-500 mt-1">
                      La préface présente le livre avant la table des matières
                    </p>
                  </div>

                  <div className="flex justify-between">
                    <button
                      type="button"
                      onClick={() => setFormStep(1)}
                      className="bg-gray-300 text-gray-700 px-6 py-3 rounded-lg font-semibold hover:bg-gray-400"
                    >
                      ← Retour
                    </button>
                    
                    <button
                      type="submit"
                      disabled={loading || formData.target_audience.length === 0}
                      className="btn-primary flex items-center justify-center px-6 py-3"
                      data-testid="generate-toc-button"
                    >
                      {loading ? (
                        <>
                          <FaSpinner className="animate-spin mr-2" />
                          Génération de la table des matières...
                        </>
                      ) : (
                        <>
                          <FaCheckCircle className="mr-2" />
                          Générer la table des matières
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>
        )}

        {/* Step 2: TOC Preview */}
        {step === 2 && (
          <div className="card">
            <h2 className="text-3xl font-bold text-gray-800 mb-6">
              Table des matières - {formData.title}
            </h2>
            <p className="text-gray-600 mb-6">Par {formData.author}</p>

            <div className="space-y-4 mb-8">
              {toc.map((chapter, index) => (
                <div key={index} className="chapter-card" data-testid={`toc-chapter-${index}`}>
                  <div className="flex items-start space-x-4">
                    <div className="bg-primary-violet text-white w-10 h-10 rounded-full flex items-center justify-center font-bold flex-shrink-0">
                      {chapter.number}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-gray-800 mb-2">{chapter.title}</h3>
                      <p className="text-gray-600 text-sm">{chapter.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => setStep(1)}
                className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-800 px-6 py-3 rounded-lg font-semibold transition-all"
                data-testid="back-to-form-button"
              >
                ← Modifier les informations
              </button>
              <button
                onClick={handleGenerateContent}
                disabled={generatingContent}
                className="flex-1 btn-primary flex items-center justify-center"
                data-testid="generate-content-button"
              >
                {generatingContent ? (
                  <>
                    <FaSpinner className="animate-spin mr-2" />
                    Génération du contenu...
                  </>
                ) : (
                  <>
                    <FaCheckCircle className="mr-2" />
                    Générer le contenu complet
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Generated Content */}
        {step === 3 && (
          <div className="card">
            <div className="text-center mb-8">
              <FaCheckCircle className="text-6xl text-green-500 mx-auto mb-4" />
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Ebook généré avec succès !</h2>
              <p className="text-gray-600">{formData.title} par {formData.author}</p>
            </div>

            <div className="space-y-6 mb-8">
              {generatedChapters.map((chapter, index) => (
                <div key={index} className="border-2 border-gray-200 rounded-lg p-6" data-testid={`generated-chapter-${index}`}>
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="bg-primary-blue text-white w-10 h-10 rounded-full flex items-center justify-center font-bold">
                      {chapter.number}
                    </div>
                    <h3 className="text-2xl font-bold text-gray-800">{chapter.title}</h3>
                  </div>
                  <div className="prose max-w-none">
                    <p className="text-gray-700 whitespace-pre-wrap">{chapter.content}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex-1 btn-primary flex items-center justify-center"
                data-testid="go-to-dashboard-button"
              >
                <FaEye className="mr-2" />
                Voir mes Ebooks
              </button>
              <button
                onClick={() => {
                  setStep(1);
                  setFormData({
                    author: '',
                    title: '',
                    tone: 'Professionnel',
                    target_audience: [],
                    description: '',
                    chapters_count: 5,
                    length: 'Moyen: 20-50 pages'
                  });
                  setToc([]);
                  setEbookId(null);
                  setGeneratedChapters([]);
                }}
                className="flex-1 btn-secondary flex items-center justify-center"
                data-testid="create-another-button"
              >
                <FaPlus className="mr-2" />
                Créer un autre Ebook
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Ebook Viewer Component
const EbookViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [ebook, setEbook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [generatingCover, setGeneratingCover] = useState(false);
  const [coverGenerated, setCoverGenerated] = useState(false);
  const [generatingLegal, setGeneratingLegal] = useState(false);
  const [legalGenerated, setLegalGenerated] = useState(false);
  const [generatingTheme, setGeneratingTheme] = useState(false);
  const [themeGenerated, setThemeGenerated] = useState(false);
  const [generatingIllustrations, setGeneratingIllustrations] = useState(false);
  const [illustrationsGenerated, setIllustrationsGenerated] = useState(false);
  
  // Edit & Regenerate states
  const [editingChapter, setEditingChapter] = useState(null);
  const [editedContent, setEditedContent] = useState('');
  const [regeneratingChapter, setRegeneratingChapter] = useState(null);
  const [regeneratingImage, setRegeneratingImage] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(null);

  useEffect(() => {
    const fetchEbook = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/ebooks/${id}`, {
          withCredentials: true
        });
        setEbook(response.data);
        // Check if cover already exists
        if (response.data.cover) {
          setCoverGenerated(true);
        }
        // Check if legal pages already exist
        if (response.data.legal_pages) {
          setLegalGenerated(true);
        }
        // Check if visual theme already exists
        if (response.data.visual_theme) {
          setThemeGenerated(true);
        }
        // Check if illustrations already exist
        if (response.data.illustrations) {
          setIllustrationsGenerated(true);
        }
      } catch (error) {
        console.error('Error fetching ebook:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchEbook();
  }, [id]);

  const handleExport = async (format) => {
    setExporting(true);
    try {
      // Récupérer le token pour l'authentification
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API_URL}/api/ebooks/${id}/export/${format}`,
        {
          responseType: 'blob',
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
          withCredentials: true
        }
      );

      // Déterminer l'extension
      const extensions = {
        pdf: 'pdf',
        epub: 'epub',
        html: 'html',
        mobi: 'epub',
        docx: 'docx'
      };

      // Créer un nom de fichier sûr
      const safeFilename = ebook?.title ? ebook.title.replace(/[^a-z0-9]/gi, '_') : 'ebook';
      const filename = `${safeFilename}.${extensions[format]}`;

      // Créer un lien de téléchargement
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setShowExportMenu(false);
    } catch (error) {
      console.error('Error exporting:', error);
      if (error.response?.status === 401) {
        alert('Session expirée. Veuillez vous reconnecter.');
      } else {
        alert(`Erreur lors de l'export: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setExporting(false);
    }
  };

  const handleGenerateCover = async () => {
    setGeneratingCover(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/generate-cover`,
        { ebook_id: id },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Mettre à jour l'ebook avec la couverture
        setEbook({ ...ebook, cover: response.data.cover });
        setCoverGenerated(true);
      }
    } catch (error) {
      console.error('Error generating cover:', error);
      if (error.response?.status === 401) {
        alert('Session expirée. Veuillez vous reconnecter.');
      } else {
        alert(`Erreur: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setGeneratingCover(false);
    }
  };

  const handleGenerateLegal = async () => {
    setGeneratingLegal(true);
    try {
      const currentYear = new Date().getFullYear();
      const response = await axios.post(
        `${API_URL}/api/ebooks/generate-legal-pages`,
        { 
          ebook_id: id,
          year: currentYear,
          edition: "Première édition"
        },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Mettre à jour l'ebook avec les pages légales
        setEbook({ ...ebook, legal_pages: response.data.legal_pages });
        setLegalGenerated(true);
      }
    } catch (error) {
      console.error('Error generating legal pages:', error);
      if (error.response?.status === 401) {
        showToast('Session expirée. Veuillez vous reconnecter.', 'error');
      } else {
        showToast(`Erreur: ${error.response?.data?.detail || error.message}`, 'error');
      }
    } finally {
      setGeneratingLegal(false);
    }
  };

  const handleGenerateTheme = async () => {
    setGeneratingTheme(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/generate-visual-theme`,
        { ebook_id: id },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Mettre à jour l'ebook avec le thème visuel
        setEbook({ ...ebook, visual_theme: response.data.visual_theme });
        setThemeGenerated(true);
      }
    } catch (error) {
      console.error('Error generating visual theme:', error);
      if (error.response?.status === 401) {
        showToast('Session expirée. Veuillez vous reconnecter.', 'error');
      } else {
        showToast(`Erreur: ${error.response?.data?.detail || error.message}`, 'error');
      }
    } finally {
      setGeneratingTheme(false);
    }
  };

  const handleGenerateIllustrations = async () => {
    setGeneratingIllustrations(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/generate-illustrations`,
        { ebook_id: id },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Mettre à jour l'ebook avec les illustrations
        setEbook({ ...ebook, illustrations: response.data.illustrations });
        setIllustrationsGenerated(true);
      }
    } catch (error) {
      console.error('Error generating illustrations:', error);
      if (error.response?.status === 401) {
        showToast('Session expirée. Veuillez vous reconnecter.', 'error');
      } else {
        showToast(`Erreur: ${error.response?.data?.detail || error.message}`, 'error');
      }
    } finally {
      setGeneratingIllustrations(false);
    }
  };

  // Edit chapter
  const handleEditChapter = (chapter) => {
    setEditingChapter(chapter.number);
    setEditedContent(chapter.content);
  };

  const handleSaveEdit = async () => {
    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/edit-chapter`,
        {
          ebook_id: id,
          chapter_number: editingChapter,
          new_content: editedContent
        },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Update local state
        const updatedChapters = ebook.chapters.map(ch =>
          ch.number === editingChapter ? { ...ch, content: editedContent } : ch
        );
        setEbook({ ...ebook, chapters: updatedChapters });
        setEditingChapter(null);
        setEditedContent('');
        showToast('Chapitre mis à jour avec succès !', 'success');
      }
    } catch (error) {
      console.error('Error editing chapter:', error);
      showToast(`Erreur: ${error.response?.data?.detail || error.message}`, 'error');
    }
  };

  // Regenerate chapter
  const handleRegenerateChapter = async (chapterNumber) => {
    setRegeneratingChapter(chapterNumber);
    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/regenerate-chapter`,
        {
          ebook_id: id,
          chapter_number: chapterNumber
        },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Update local state
        const updatedChapters = ebook.chapters.map(ch =>
          ch.number === chapterNumber ? { ...ch, content: response.data.new_content } : ch
        );
        setEbook({ ...ebook, chapters: updatedChapters });
        alert('Chapitre régénéré avec succès !');
      }
    } catch (error) {
      console.error('Error regenerating chapter:', error);
      alert(`Erreur: ${error.response?.data?.detail || error.message}`);
    } finally {
      setRegeneratingChapter(null);
    }
  };

  // Regenerate image
  const handleRegenerateImage = async (chapterNumber, imageIndex) => {
    setRegeneratingImage(`${chapterNumber}-${imageIndex}`);
    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/regenerate-image`,
        {
          ebook_id: id,
          chapter_number: chapterNumber,
          illustration_index: imageIndex
        },
        {
          headers: { 'Content-Type': 'application/json' },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Update local state with new image
        const updatedIllustrations = ebook.illustrations.map(ill => {
          if (ill.chapter_number === chapterNumber) {
            const updatedImages = [...ill.images];
            updatedImages[imageIndex] = {
              ...updatedImages[imageIndex],
              image_base64: response.data.image_base64
            };
            return { ...ill, images: updatedImages };
          }
          return ill;
        });
        setEbook({ ...ebook, illustrations: updatedIllustrations });
        alert('Image régénérée avec succès !');
      }
    } catch (error) {
      console.error('Error regenerating image:', error);
      alert(`Erreur: ${error.response?.data?.detail || error.message}`);
    } finally {
      setRegeneratingImage(null);
    }
  };

  // Upload custom image
  const handleUploadImage = async (chapterNumber, event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploadingImage(chapterNumber);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        `${API_URL}/api/ebooks/upload-custom-image?ebook_id=${id}&chapter_number=${chapterNumber}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          withCredentials: true
        }
      );

      if (response.data.success) {
        // Refresh ebook data
        const ebookResponse = await axios.get(`${API_URL}/api/ebooks/${id}`, {
          withCredentials: true
        });
        setEbook(ebookResponse.data);
        alert('Image uploadée avec succès !');
      }
    } catch (error) {
      console.error('Error uploading image:', error);
      alert(`Erreur: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploadingImage(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!ebook) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="card text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Ebook non trouvé</h2>
          <button onClick={() => navigate('/dashboard')} className="btn-primary">
            Retour au Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="gradient-bg text-white p-4 shadow-lg">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <FaBook className="text-3xl" />
            <h1 className="text-2xl font-bold">YooCreat</h1>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-all"
            data-testid="back-to-dashboard"
          >
            ← Retour au Dashboard
          </button>
        </div>
      </nav>

      <div className="container mx-auto p-8 max-w-5xl">
        {/* Header avec actions */}
        <div className="card mb-6">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <h1 className="text-4xl font-bold text-gray-800 mb-2" data-testid="ebook-title">{ebook.title}</h1>
              <p className="text-xl text-gray-600 mb-4">Par {ebook.author}</p>
              <p className="text-gray-700 mb-4">{ebook.description}</p>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>📚 {ebook.chapters_count} chapitres</span>
                <span>📄 {ebook.length}</span>
                <span>🎭 Ton: {ebook.tone}</span>
              </div>
            </div>

            {/* Boutons d'action */}
            <div className="flex flex-col space-y-3 ml-6">
              {/* Bouton Export */}
              <div className="relative">
                <button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  className="bg-gradient-to-r from-primary-blue to-primary-violet text-white px-6 py-3 rounded-lg font-semibold hover:shadow-lg transition-all flex items-center space-x-2 whitespace-nowrap"
                  data-testid="export-button"
                >
                  <span>📤</span>
                  <span>Exporter</span>
                </button>

                {/* Menu d'export */}
                {showExportMenu && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-xl border-2 border-gray-200 z-10">
                    <div className="p-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleExport('pdf'); }}
                        disabled={exporting}
                        className="w-full text-left px-4 py-3 rounded-md hover:bg-blue-50 transition-all flex items-center space-x-3"
                        data-testid="export-pdf"
                      >
                        <span className="text-2xl">📄</span>
                        <div>
                          <div className="font-semibold text-gray-800">PDF</div>
                          <div className="text-xs text-gray-500">Impression professionnelle</div>
                        </div>
                      </button>

                      <button
                        onClick={(e) => { e.stopPropagation(); handleExport('epub'); }}
                        disabled={exporting}
                        className="w-full text-left px-4 py-3 rounded-md hover:bg-purple-50 transition-all flex items-center space-x-3"
                        data-testid="export-epub"
                      >
                        <span className="text-2xl">📖</span>
                        <div>
                          <div className="font-semibold text-gray-800">EPUB</div>
                          <div className="text-xs text-gray-500">Liseuses électroniques</div>
                        </div>
                      </button>

                      <button
                        onClick={(e) => { e.stopPropagation(); handleExport('html'); }}
                        disabled={exporting}
                        className="w-full text-left px-4 py-3 rounded-md hover:bg-orange-50 transition-all flex items-center space-x-3"
                        data-testid="export-html"
                      >
                        <span className="text-2xl">🌐</span>
                        <div>
                          <div className="font-semibold text-gray-800">HTML</div>
                          <div className="text-xs text-gray-500">Flipbook interactif</div>
                        </div>
                      </button>

                      <button
                        onClick={(e) => { e.stopPropagation(); handleExport('docx'); }}
                        disabled={exporting}
                        className="w-full text-left px-4 py-3 rounded-md hover:bg-blue-50 transition-all flex items-center space-x-3"
                        data-testid="export-docx"
                      >
                        <span className="text-2xl">📝</span>
                        <div>
                          <div className="font-semibold text-gray-800">DOCX</div>
                          <div className="text-xs text-gray-500">Édition Word</div>
                        </div>
                      </button>

                      <button
                        onClick={(e) => { e.stopPropagation(); handleExport('mobi'); }}
                        disabled={exporting}
                        className="w-full text-left px-4 py-3 rounded-md hover:bg-green-50 transition-all flex items-center space-x-3"
                        data-testid="export-mobi"
                      >
                        <span className="text-2xl">📚</span>
                        <div>
                          <div className="font-semibold text-gray-800">MOBI</div>
                          <div className="text-xs text-gray-500">Kindle</div>
                        </div>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Bouton Générer Couverture */}
              <button
                onClick={handleGenerateCover}
                disabled={generatingCover}
                className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center space-x-2 whitespace-nowrap ${
                  coverGenerated
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-primary-orange text-white hover:bg-primary-orange-dark'
                }`}
                data-testid="generate-cover-button"
              >
                {generatingCover ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Génération...</span>
                  </>
                ) : coverGenerated ? (
                  <>
                    <FaCheckCircle />
                    <span>Couverture OK</span>
                  </>
                ) : (
                  <>
                    <span>🎨</span>
                    <span>Générer Couverture</span>
                  </>
                )}
              </button>

              {/* Bouton Générer Pages Légales */}
              <button
                onClick={handleGenerateLegal}
                disabled={generatingLegal}
                className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center space-x-2 whitespace-nowrap ${
                  legalGenerated
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-primary-violet text-white hover:bg-primary-violet-dark'
                }`}
                data-testid="generate-legal-button"
              >
                {generatingLegal ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Génération...</span>
                  </>
                ) : legalGenerated ? (
                  <>
                    <FaCheckCircle />
                    <span>Pages Légales OK</span>
                  </>
                ) : (
                  <>
                    <span>⚖️</span>
                    <span>Générer Pages Légales</span>
                  </>
                )}
              </button>

              {/* Bouton Générer Thème Visuel */}
              <button
                onClick={handleGenerateTheme}
                disabled={generatingTheme}
                className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center space-x-2 whitespace-nowrap ${
                  themeGenerated
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:from-blue-600 hover:to-purple-600'
                }`}
                data-testid="generate-theme-button"
              >
                {generatingTheme ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Génération...</span>
                  </>
                ) : themeGenerated ? (
                  <>
                    <FaCheckCircle />
                    <span>Thème Visuel OK</span>
                  </>
                ) : (
                  <>
                    <span>🎨</span>
                    <span>Générer Thème Visuel</span>
                  </>
                )}
              </button>

              {/* Bouton Générer Illustrations */}
              <button
                onClick={handleGenerateIllustrations}
                disabled={generatingIllustrations || !ebook.chapters || ebook.chapters.length === 0}
                className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center space-x-2 whitespace-nowrap ${
                  illustrationsGenerated
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : (!ebook.chapters || ebook.chapters.length === 0)
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-pink-500 to-orange-500 text-white hover:from-pink-600 hover:to-orange-600'
                }`}
                data-testid="generate-illustrations-button"
                title={!ebook.chapters || ebook.chapters.length === 0 ? 'Générez le contenu d\'abord' : ''}
              >
                {generatingIllustrations ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Génération...</span>
                  </>
                ) : illustrationsGenerated ? (
                  <>
                    <FaCheckCircle />
                    <span>Illustrations OK</span>
                  </>
                ) : (
                  <>
                    <span>🖼️</span>
                    <span>Générer Illustrations</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Affichage de la couverture générée */}
        {ebook.cover && (
          <div className="card mb-6" data-testid="cover-display">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">📐 Design de Couverture</h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* Visuel de la couverture */}
              <div 
                className="rounded-lg p-8 text-center flex flex-col justify-center"
                style={{
                  background: ebook.cover.design?.colors 
                    ? `linear-gradient(135deg, ${ebook.cover.design.colors[0]}, ${ebook.cover.design.colors[1]})`
                    : 'linear-gradient(135deg, #3B82F6, #8B5CF6)'
                }}
              >
                <h3 className="text-3xl font-bold text-white mb-4">{ebook.cover.title}</h3>
                <p className="text-xl text-white/90 mb-6">par {ebook.cover.author}</p>
                {ebook.cover.subtitle && (
                  <p className="text-lg text-yellow-300 italic">{ebook.cover.subtitle}</p>
                )}
              </div>

              {/* Détails du design */}
              <div className="space-y-4">
                <div>
                  <h3 className="font-bold text-gray-700 mb-2">🎨 Palette de couleurs</h3>
                  <div className="flex space-x-2">
                    {ebook.cover.design?.colors?.map((color, idx) => (
                      <div
                        key={idx}
                        className="w-12 h-12 rounded-md shadow"
                        style={{ backgroundColor: color }}
                        title={color}
                      ></div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-bold text-gray-700 mb-2">✏️ Style</h3>
                  <p className="text-gray-600">{ebook.cover.design?.style}</p>
                </div>

                {ebook.cover.tagline && (
                  <div>
                    <h3 className="font-bold text-gray-700 mb-2">💬 Accroche</h3>
                    <p className="text-gray-600 italic">"{ebook.cover.tagline}"</p>
                  </div>
                )}

                {ebook.cover.typography && (
                  <div>
                    <h3 className="font-bold text-gray-700 mb-2">🔤 Typographie</h3>
                    <p className="text-gray-600">{ebook.cover.typography.title_font}</p>
                    <p className="text-sm text-gray-500">{ebook.cover.typography.style_notes}</p>
                  </div>
                )}
              </div>
            </div>

            {ebook.cover.back_cover_text && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-bold text-gray-700 mb-2">📄 Texte de dos de couverture</h3>
                <p className="text-gray-600">{ebook.cover.back_cover_text}</p>
              </div>
            )}
          </div>
        )}

        {/* Affichage des pages légales générées */}
        {ebook.legal_pages && (
          <div className="card mb-6" data-testid="legal-display">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">⚖️ Pages Légales</h2>
            
            <div className="space-y-6">
              {/* Copyright */}
              {ebook.legal_pages.copyright_page && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-bold text-gray-700 mb-3 flex items-center">
                    <span className="mr-2">©</span>
                    Copyright
                  </h3>
                  <div className="text-gray-600 text-sm whitespace-pre-wrap">
                    {ebook.legal_pages.copyright_page}
                  </div>
                </div>
              )}

              {/* Legal Mentions */}
              {ebook.legal_pages.legal_mentions && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-bold text-gray-700 mb-3">Mentions Légales</h3>
                  <div className="text-gray-600 text-sm whitespace-pre-wrap">
                    {ebook.legal_pages.legal_mentions}
                  </div>
                </div>
              )}

              {/* ISBN & Edition Info */}
              <div className="grid md:grid-cols-3 gap-4">
                {ebook.legal_pages.isbn && ebook.legal_pages.isbn !== 'Non attribué' && (
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h3 className="font-bold text-blue-700 mb-2">ISBN</h3>
                    <p className="text-blue-600 text-sm">{ebook.legal_pages.isbn}</p>
                  </div>
                )}
                
                {ebook.legal_pages.publisher && (
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <h3 className="font-bold text-purple-700 mb-2">Éditeur</h3>
                    <p className="text-purple-600 text-sm">{ebook.legal_pages.publisher}</p>
                  </div>
                )}
                
                {ebook.legal_pages.edition && (
                  <div className="p-4 bg-orange-50 rounded-lg">
                    <h3 className="font-bold text-orange-700 mb-2">Édition</h3>
                    <p className="text-orange-600 text-sm">{ebook.legal_pages.edition} - {ebook.legal_pages.year}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Affichage du thème visuel généré */}
        {ebook.visual_theme && (
          <div className="card mb-6" data-testid="theme-display">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">🎨 Thème Visuel</h2>
            
            <div className="space-y-6">
              {/* Overall Mood */}
              {ebook.visual_theme.overall_mood && (
                <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                  <p className="text-gray-700 italic text-center">{ebook.visual_theme.overall_mood}</p>
                </div>
              )}

              {/* Palette de Couleurs */}
              {ebook.visual_theme.palette && (
                <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                  <h3 className="font-bold text-gray-700 mb-3 flex items-center">
                    <span className="mr-2">🎨</span>
                    Palette de Couleurs
                  </h3>
                  <div className="grid grid-cols-3 gap-4 mb-3">
                    <div className="text-center">
                      <div 
                        className="w-full h-20 rounded-lg shadow-md mb-2" 
                        style={{ backgroundColor: ebook.visual_theme.palette.primary }}
                      ></div>
                      <p className="text-xs font-semibold text-gray-600">Primaire</p>
                      <p className="text-xs text-gray-500">{ebook.visual_theme.palette.primary}</p>
                    </div>
                    <div className="text-center">
                      <div 
                        className="w-full h-20 rounded-lg shadow-md mb-2" 
                        style={{ backgroundColor: ebook.visual_theme.palette.secondary }}
                      ></div>
                      <p className="text-xs font-semibold text-gray-600">Secondaire</p>
                      <p className="text-xs text-gray-500">{ebook.visual_theme.palette.secondary}</p>
                    </div>
                    <div className="text-center">
                      <div 
                        className="w-full h-20 rounded-lg shadow-md mb-2" 
                        style={{ backgroundColor: ebook.visual_theme.palette.background }}
                      ></div>
                      <p className="text-xs font-semibold text-gray-600">Arrière-plan</p>
                      <p className="text-xs text-gray-500">{ebook.visual_theme.palette.background}</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{ebook.visual_theme.palette.justification}</p>
                </div>
              )}

              {/* Polices */}
              {ebook.visual_theme.fonts && (
                <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                  <h3 className="font-bold text-gray-700 mb-3 flex items-center">
                    <span className="mr-2">🔤</span>
                    Polices de Caractères
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4 mb-3">
                    <div className="p-3 bg-gray-50 rounded">
                      <p className="text-xs text-gray-500 mb-1">Corps du Texte</p>
                      <p className="text-lg font-semibold" style={{ fontFamily: ebook.visual_theme.fonts.body }}>
                        {ebook.visual_theme.fonts.body}
                      </p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded">
                      <p className="text-xs text-gray-500 mb-1">Titres</p>
                      <p className="text-lg font-bold" style={{ fontFamily: ebook.visual_theme.fonts.titles }}>
                        {ebook.visual_theme.fonts.titles}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">{ebook.visual_theme.fonts.justification}</p>
                </div>
              )}

              {/* Style de Citations */}
              {ebook.visual_theme.quote_style && (
                <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                  <h3 className="font-bold text-gray-700 mb-3 flex items-center">
                    <span className="mr-2">💬</span>
                    Style des Citations/Encadrés
                  </h3>
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="text-3xl">{ebook.visual_theme.quote_style.icon}</span>
                    <div>
                      <p className="font-semibold text-gray-700 capitalize">{ebook.visual_theme.quote_style.type}</p>
                      <p className="text-sm text-gray-600">{ebook.visual_theme.quote_style.description}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Séparateur de Chapitre */}
              {ebook.visual_theme.chapter_separator && (
                <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
                  <h3 className="font-bold text-gray-700 mb-3 flex items-center">
                    <span className="mr-2">✨</span>
                    Séparateur de Chapitre
                  </h3>
                  <div className="flex items-center space-x-3">
                    <span className="text-3xl">{ebook.visual_theme.chapter_separator.symbol}</span>
                    <div>
                      <p className="font-semibold text-gray-700 capitalize">{ebook.visual_theme.chapter_separator.type}</p>
                      <p className="text-sm text-gray-600">{ebook.visual_theme.chapter_separator.description}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Affichage des illustrations générées */}
        {ebook.illustrations && ebook.illustrations.length > 0 && (
          <div className="card mb-6" data-testid="illustrations-display">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">🖼️ Illustrations Générées par IA</h2>
            
            <div className="space-y-6">
              {ebook.illustrations.map((chapterIllust, idx) => (
                <div key={idx} className="border-2 border-gray-200 rounded-lg p-4">
                  <h3 className="font-bold text-gray-700 mb-3">
                    Chapitre {chapterIllust.chapter_number}
                  </h3>
                  
                  <div className="space-y-4">
                    {chapterIllust.images && chapterIllust.images.map((img, imgIdx) => (
                      <div key={imgIdx} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex flex-col gap-4">
                          {/* Image Preview */}
                          {img.image_base64 ? (
                            <div className="w-full">
                              <img 
                                src={`data:image/png;base64,${img.image_base64}`}
                                alt={img.alt_text}
                                className="w-full max-w-2xl mx-auto rounded-lg shadow-md"
                              />
                            </div>
                          ) : img.error ? (
                            <div className="bg-red-50 border border-red-200 rounded p-4 text-center">
                              <p className="text-red-600">❌ Erreur de génération: {img.error}</p>
                            </div>
                          ) : (
                            <div className="bg-gray-200 rounded p-4 text-center">
                              <p className="text-gray-500">Image en cours de génération...</p>
                            </div>
                          )}
                          
                          {/* Details */}
                          <div>
                            <p className="text-sm text-gray-600 mb-2">
                              <strong>Description :</strong> {img.alt_text}
                            </p>
                            {img.dalle_prompt && (
                              <p className="text-xs text-gray-500 italic mb-2">
                                <strong>Prompt DALL-E :</strong> {img.dalle_prompt}
                              </p>
                            )}
                            <p className="text-xs text-gray-500">
                              <strong>Placement suggéré :</strong> {img.placement}
                            </p>
                            {img.image_source && (
                              <p className="text-xs text-gray-400 mt-2">
                                Source : {img.image_source === 'dall-e' ? 'Généré par DALL-E' : 'Upload utilisateur'}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Contenu des chapitres */}
        {ebook.chapters && ebook.chapters.length > 0 ? (
          <div className="space-y-6">
            {ebook.chapters.map((chapter, index) => (
              <div key={index} className="card" data-testid={`chapter-${index}`}>
                {/* Chapter Header with Actions */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="bg-primary-violet text-white w-10 h-10 rounded-full flex items-center justify-center font-bold">
                      {chapter.number}
                    </div>
                    <h2 className="text-2xl font-bold text-gray-800">{chapter.title}</h2>
                  </div>
                  
                  {/* Action Buttons */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleEditChapter(chapter)}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center space-x-2"
                      title="Éditer le chapitre"
                    >
                      <span>✏️</span>
                      <span>Éditer</span>
                    </button>
                    
                    <button
                      onClick={() => handleRegenerateChapter(chapter.number)}
                      disabled={regeneratingChapter === chapter.number}
                      className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 flex items-center space-x-2 disabled:opacity-50"
                      title="Régénérer le texte avec IA"
                    >
                      {regeneratingChapter === chapter.number ? (
                        <>
                          <FaSpinner className="animate-spin" />
                          <span>Régénération...</span>
                        </>
                      ) : (
                        <>
                          <span>🔄</span>
                          <span>Régénérer</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
                
                {/* Chapter Content or Edit Mode */}
                {editingChapter === chapter.number ? (
                  <div className="space-y-4">
                    <textarea
                      className="w-full input-field"
                      rows="15"
                      value={editedContent}
                      onChange={(e) => setEditedContent(e.target.value)}
                    ></textarea>
                    <div className="flex space-x-2">
                      <button
                        onClick={handleSaveEdit}
                        className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 font-semibold"
                      >
                        💾 Enregistrer
                      </button>
                      <button
                        onClick={() => {
                          setEditingChapter(null);
                          setEditedContent('');
                        }}
                        className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 font-semibold"
                      >
                        Annuler
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="prose max-w-none">
                    <p className="text-gray-700 whitespace-pre-wrap">{chapter.content}</p>
                  </div>
                )}
                
                {/* Chapter Illustrations */}
                {ebook.illustrations && ebook.illustrations.find(ill => ill.chapter_number === chapter.number) && (
                  <div className="mt-6 border-t pt-6">
                    <h3 className="text-lg font-bold text-gray-800 mb-4">🖼️ Illustrations</h3>
                    <div className="space-y-4">
                      {ebook.illustrations
                        .find(ill => ill.chapter_number === chapter.number)
                        ?.images?.map((img, imgIdx) => (
                          <div key={imgIdx} className="bg-gray-50 p-4 rounded-lg">
                            {/* Image Display */}
                            {img.image_base64 && (
                              <img
                                src={`data:image/png;base64,${img.image_base64}`}
                                alt={img.alt_text || 'Illustration'}
                                className="w-full max-w-2xl mx-auto rounded-lg shadow-md mb-3"
                              />
                            )}
                            
                            {/* Image Info */}
                            <p className="text-sm text-gray-600 mb-2">
                              <strong>Description :</strong> {img.alt_text}
                            </p>
                            {img.dalle_prompt && (
                              <p className="text-xs text-gray-500 italic mb-3">
                                Prompt DALL-E : {img.dalle_prompt}
                              </p>
                            )}
                            
                            {/* Image Actions */}
                            <div className="flex space-x-2">
                              <button
                                onClick={() => handleRegenerateImage(chapter.number, imgIdx)}
                                disabled={regeneratingImage === `${chapter.number}-${imgIdx}`}
                                className="px-3 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 text-sm disabled:opacity-50"
                              >
                                {regeneratingImage === `${chapter.number}-${imgIdx}` ? (
                                  <><FaSpinner className="animate-spin inline mr-1" /> Régénération...</>
                                ) : (
                                  '🔄 Régénérer Image'
                                )}
                              </button>
                            </div>
                          </div>
                        ))}
                    </div>
                    
                    {/* Upload Custom Image Button */}
                    <div className="mt-4">
                      <label className="cursor-pointer inline-block px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">
                        {uploadingImage === chapter.number ? (
                          <><FaSpinner className="animate-spin inline mr-2" /> Upload en cours...</>
                        ) : (
                          <>📸 Ajouter une image personnalisée</>
                        )}
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={(e) => handleUploadImage(chapter.number, e)}
                          className="hidden"
                          disabled={uploadingImage === chapter.number}
                        />
                      </label>
                      <p className="text-xs text-gray-500 mt-1">Formats acceptés : JPG, PNG, WebP</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="card text-center py-8">
            <p className="text-gray-600">Ce livre est encore en brouillon. Le contenu n'a pas encore été généré.</p>
          </div>
        )}
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="spinner"></div>
      </div>
    );
  }

  return token ? children : <Navigate to="/" />;
};

// Main App Component
function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/" element={<AuthPage />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/create"
              element={
                <ProtectedRoute>
                  <EbookCreator />
                </ProtectedRoute>
              }
            />
            <Route
              path="/ebook/:id"
              element={
                <ProtectedRoute>
                  <EbookViewer />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Router>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
