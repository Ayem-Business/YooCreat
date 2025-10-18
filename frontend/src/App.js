import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FaBook, FaSignOutAlt, FaPlus, FaSpinner, FaCheckCircle, FaEye, FaGoogle } from 'react-icons/fa';
import './App.css';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/auth/me`);
      setUser(response.data);
    } catch (error) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = (token, userData) => {
    localStorage.setItem('token', token);
    setToken(token);
    setUser(userData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  };

  const logout = () => {
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
  const { login } = useAuth();
  const navigate = useNavigate();

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
    // Simplified Google login - in production, use proper OAuth flow
    alert('Connexion Google: Cette fonctionnalité nécessite la configuration OAuth2 complète via Emergent. Pour l\'instant, utilisez l\'inscription par email.');
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
    length: 'Moyen: 20-50 pages'
  });
  const [toc, setToc] = useState([]);
  const [ebookId, setEbookId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generatingContent, setGeneratingContent] = useState(false);
  const [generatedChapters, setGeneratedChapters] = useState([]);
  const [error, setError] = useState('');

  const tones = ['Professionnel', 'Conversationnel', 'Académique', 'Humoristique', 'Inspirant', 'Technique', 'Storytelling'];
  const audiences = ['Enfants', 'Adolescents', 'Adultes', 'Professionnels', 'Seniors', 'Débutants', 'Experts'];
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
            <form onSubmit={handleGenerateTOC} className="space-y-6">
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

              <button
                type="submit"
                disabled={loading || formData.target_audience.length === 0}
                className="btn-primary w-full flex items-center justify-center"
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
  const [ebook, setEbook] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEbook();
  }, [id]);

  const fetchEbook = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/ebooks/${id}`);
      setEbook(response.data);
    } catch (error) {
      console.error('Error fetching ebook:', error);
    } finally {
      setLoading(false);
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
          >
            ← Retour au Dashboard
          </button>
        </div>
      </nav>

      <div className="container mx-auto p-8 max-w-4xl">
        <div className="card mb-6">
          <h1 className="text-4xl font-bold text-gray-800 mb-2" data-testid="ebook-title">{ebook.title}</h1>
          <p className="text-xl text-gray-600 mb-4">Par {ebook.author}</p>
          <p className="text-gray-700 mb-4">{ebook.description}</p>
          <div className="flex items-center space-x-4 text-sm text-gray-500">
            <span>📚 {ebook.chapters_count} chapitres</span>
            <span>📄 {ebook.length}</span>
            <span>🎭 Ton: {ebook.tone}</span>
          </div>
        </div>

        {ebook.chapters && ebook.chapters.length > 0 ? (
          <div className="space-y-6">
            {ebook.chapters.map((chapter, index) => (
              <div key={index} className="card" data-testid={`chapter-${index}`}>
                <div className="flex items-center space-x-3 mb-4">
                  <div className="bg-primary-violet text-white w-10 h-10 rounded-full flex items-center justify-center font-bold">
                    {chapter.number}
                  </div>
                  <h2 className="text-2xl font-bold text-gray-800">{chapter.title}</h2>
                </div>
                <div className="prose max-w-none">
                  <p className="text-gray-700 whitespace-pre-wrap">{chapter.content}</p>
                </div>
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

// Import useParams for EbookViewer
import { useParams } from 'react-router-dom';

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
  );
}

export default App;
