from fastapi import FastAPI, HTTPException, Depends, status, Response, Request, Cookie, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from pymongo import MongoClient
from bson import ObjectId
import gridfs
import os
from dotenv import load_dotenv
import asyncio
import httpx
import base64
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
from exporter import EbookExporter

load_dotenv()

app = FastAPI(title="YooCreat API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:8001",
        "https://smart-ebook-gen-1.preview.emergentagent.com",
        "https://smart-ebook-gen-1.preview.emergentagent.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
client = MongoClient(os.getenv("MONGO_URL"))
db = client.yoocreat
users_collection = db.users
ebooks_collection = db.ebooks
user_sessions_collection = db.user_sessions

# GridFS for image storage
fs = gridfs.GridFS(db)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuth(BaseModel):
    session_id: str

class GoogleSessionData(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    session_token: str

class EbookCreate(BaseModel):
    author: str
    title: str
    tone: str
    target_audience: List[str]
    description: str
    chapters_count: int = Field(ge=1, le=50)
    length: str
    genre: Optional[str] = None
    about_author: Optional[str] = None
    acknowledgments: Optional[str] = None
    preface: Optional[str] = None

class GenerateTOC(BaseModel):
    author: str
    title: str
    tone: str
    target_audience: List[str]
    description: str
    chapters_count: int
    length: str

class GenerateContent(BaseModel):
    ebook_id: str
    toc: List[Dict[str, Any]]

class GenerateVisualThemeRequest(BaseModel):
    ebook_id: str

class GenerateIllustrationsRequest(BaseModel):
    ebook_id: str

class EditChapterRequest(BaseModel):
    ebook_id: str
    chapter_number: int
    new_content: str

class RegenerateChapterRequest(BaseModel):
    ebook_id: str
    chapter_number: int

class RegenerateImageRequest(BaseModel):
    ebook_id: str
    chapter_number: int
    illustration_index: int

# Helper Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", 43200)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    # Priority 1: Check session_token from cookie
    token = session_token
    
    # Priority 2: Check Authorization header (JWT or session_token)
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # First try as session_token (Emergent OAuth)
    session = user_sessions_collection.find_one({"session_token": token})
    if session:
        # Check if session is expired
        if session["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        
        user = users_collection.find_one({"_id": session["user_id"]})
        if user:
            return user
    
    # Then try as JWT token (email/password auth)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = users_collection.find_one({"_id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "YooCreat API"}

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    # Check if user exists
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if users_collection.find_one({"username": user_data.username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    user_id = f"user_{datetime.utcnow().timestamp()}".replace(".", "_")
    user = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "google_id": None,
        "created_at": datetime.utcnow().isoformat()
    }
    users_collection.insert_one(user)
    
    # Create token
    token = create_access_token({"sub": user_id, "email": user_data.email})
    
    return {
        "token": token,
        "user": {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email
        }
    }

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    user = users_collection.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["_id"], "email": user["email"]})
    
    return {
        "token": token,
        "user": {
            "id": user["_id"],
            "username": user["username"],
            "email": user["email"]
        }
    }

@app.post("/api/auth/google")
async def google_auth(auth_data: GoogleAuth, response: Response):
    """
    Process Google OAuth authentication via Emergent
    1. Frontend sends session_id from URL fragment
    2. Backend exchanges session_id for user data and session_token
    3. Store session and return user data with cookie
    """
    try:
        # Exchange session_id for user data
        async with httpx.AsyncClient() as client:
            api_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": auth_data.session_id},
                timeout=10.0
            )
            
            if api_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session ID")
            
            session_data = api_response.json()
        
        # Check if user exists
        user = users_collection.find_one({"email": session_data["email"]})
        
        if not user:
            # Create new user
            user_id = f"user_{datetime.now(timezone.utc).timestamp()}".replace(".", "_")
            user = {
                "_id": user_id,
                "username": session_data["name"],
                "email": session_data["email"],
                "password_hash": None,
                "google_id": session_data["id"],
                "picture": session_data.get("picture"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            users_collection.insert_one(user)
        else:
            user_id = user["_id"]
            # Update google_id and picture if not set
            if not user.get("google_id"):
                users_collection.update_one(
                    {"_id": user_id},
                    {"$set": {
                        "google_id": session_data["id"],
                        "picture": session_data.get("picture")
                    }}
                )
        
        # Store session in database (7 days expiry)
        session_token = session_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        user_sessions_collection.insert_one({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return {
            "success": True,
            "session_token": session_token,
            "user": {
                "id": user_id,
                "username": user.get("username"),
                "email": session_data["email"],
                "picture": session_data.get("picture")
            }
        }
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to auth service: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@app.get("/api/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "picture": current_user.get("picture")
    }

@app.post("/api/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user by deleting session and clearing cookie"""
    if session_token:
        # Delete session from database
        user_sessions_collection.delete_one({"session_token": session_token})
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"success": True, "message": "Logged out successfully"}

@app.post("/api/ebooks/generate-toc")
async def generate_toc(data: GenerateTOC, current_user = Depends(get_current_user)):
    try:
        # Create enhanced prompt for TOC generation
        prompt = f"""Tu es un expert en création de livres et structuration de contenu littéraire professionnel.

CONTEXTE DU LIVRE :
- Titre : {data.title}
- Auteur : {data.author}
- Ton : {data.tone}
- Public cible : {', '.join(data.target_audience)}
- Description/Objectif : {data.description}
- Nombre de chapitres : {data.chapters_count}
- Longueur : {data.length}

MISSION :
Crée une structure de livre DÉTAILLÉE, COHÉRENTE et PROFESSIONNELLE avec :
1. Une INTRODUCTION captivante (chapitre 0)
2. {data.chapters_count} chapitres de contenu principal (numérotés 1 à {data.chapters_count})
3. Une CONCLUSION percutante (dernier chapitre)

EXIGENCES pour chaque chapitre :
- Numéro : 0 pour intro, 1-{data.chapters_count} pour chapitres, {data.chapters_count + 1} pour conclusion
- Titre : Accrocheur, pertinent, adapté au ton {data.tone}
- Description : 2-3 phrases décrivant le contenu et la progression logique
- Sous-titres : OBLIGATOIRE - 2-4 sous-titres par chapitre qui détaillent les sections principales
- Assure une PROGRESSION NATURELLE d'un chapitre à l'autre
- Intègre des TRANSITIONS conceptuelles entre chapitres
- Langage : 100% en français

Réponds UNIQUEMENT avec ce JSON valide (sans markdown, sans texte avant/après) :
{{
  "chapters": [
    {{
      "number": 0,
      "title": "Introduction",
      "description": "Accroche le lecteur, présente le sujet et annonce les bénéfices",
      "subtitles": ["Pourquoi ce livre maintenant ?", "Ce que vous allez découvrir", "Comment tirer le meilleur parti de votre lecture"],
      "type": "introduction"
    }},
    {{
      "number": 1,
      "title": "Premier chapitre...",
      "description": "Description détaillée...",
      "subtitles": ["Sous-titre 1", "Sous-titre 2", "Sous-titre 3"],
      "type": "chapter"
    }},
    ...
    {{
      "number": {data.chapters_count + 1},
      "title": "Conclusion",
      "description": "Synthèse, call-to-action et ouverture",
      "subtitles": ["Les enseignements clés", "Vos prochaines étapes", "La vision de votre transformation"],
      "type": "conclusion"
    }}
  ]
}}"""

        # Initialize LLM Chat
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"toc_{current_user['_id']}_{datetime.utcnow().timestamp()}",
            system_message="Tu es un assistant expert en création de contenu littéraire et structuration de livres."
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse response
        import json
        # Clean response - remove markdown code blocks if present
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        toc_data = json.loads(clean_response)
        
        return {
            "success": True,
            "toc": toc_data["chapters"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TOC: {str(e)}")

@app.post("/api/ebooks/generate-content")
async def generate_content(data: GenerateContent, current_user = Depends(get_current_user)):
    try:
        # Get ebook
        ebook = ebooks_collection.find_one({"_id": data.ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        chapters = []
        previous_chapter_summary = ""
        
        for idx, chapter in enumerate(data.toc):
            chapter_type = chapter.get('type', 'chapter')
            
            # Prompt adapté selon le type de chapitre
            if chapter_type == 'introduction':
                prompt = f"""Tu es un auteur professionnel spécialisé en introductions captivantes.

CONTEXTE DU LIVRE :
- Titre : "{ebook['title']}"
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Objectif : {ebook['description']}

MISSION : Rédige une INTRODUCTION percutante (900-1200 mots) structurée ainsi :

1. **OUVERTURE CAPTIVANTE** (2-3 paragraphes)
   - Une anecdote personnelle, histoire marquante ou statistique surprenante
   - Questions qui interpellent directement le lecteur
   - Établis une connexion émotionnelle immédiate

2. **LE POURQUOI** (2-3 paragraphes)
   - Présente le problème ou besoin auquel répond ce livre
   - Explique pourquoi c'est important MAINTENANT
   - Crée l'urgence et la pertinence

3. **LA PROMESSE** (2-3 paragraphes)
   - Énonce clairement les bénéfices concrets pour le lecteur
   - Liste 3-4 choses spécifiques qu'il va apprendre ou accomplir
   - Témoigne de la transformation possible

4. **LA FEUILLE DE ROUTE** (1-2 paragraphes)
   - Donne un aperçu du parcours à venir (sans détailler chaque chapitre)
   - Crée l'anticipation et l'excitation pour la lecture
   - Termine sur une note motivante qui donne envie de tourner la page

EXIGENCES STRICTES :
- Style : {ebook['tone']}, adapté à {', '.join(ebook['target_audience'])}
- ⚠️ INTERDIT : N'utilise JAMAIS les symboles #, ##, ### ou autres balises Markdown
- ⚠️ INTERDIT : Ne répète JAMAIS le mot "Introduction" dans le texte
- Structure : Utilise UNIQUEMENT le format "🔹 Titre de section" si nécessaire pour des sous-parties
- Ton : Engageant, personnel, et orienté vers l'action
- Langage : 100% en français

Réponds UNIQUEMENT avec le texte de l'introduction (le titre "Introduction" sera ajouté automatiquement)."""

            elif chapter_type == 'conclusion':
                prompt = f"""Tu es un auteur professionnel spécialisé en conclusions mémorables et inspirantes.

CONTEXTE DU LIVRE :
- Titre : "{ebook['title']}"
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Parcours du livre : {ebook['description']}

MISSION : Rédige une CONCLUSION puissante (900-1200 mots) structurée ainsi :

1. **LE VOYAGE ACCOMPLI** (2-3 paragraphes)
   - Rappelle le point de départ (où était le lecteur au début)
   - Célèbre le chemin parcouru
   - Reconnais l'effort et l'engagement du lecteur

2. **LES ENSEIGNEMENTS CLÉS** (2-3 paragraphes)
   - Synthèse des 4-5 points principaux du livre
   - Reformule les messages essentiels de manière mémorable
   - Utilise des formulations impactantes qui restent en tête

3. **LE PASSAGE À L'ACTION** (2-3 paragraphes)
   - Liste 3-4 actions concrètes que le lecteur peut entreprendre DÈS MAINTENANT
   - Donne des étapes spécifiques et réalisables
   - Crée un sentiment d'urgence positive et d'enthousiasme

4. **LA VISION INSPIRANTE** (2 paragraphes)
   - Peins le tableau de la transformation possible
   - Projette le lecteur dans son futur réussi
   - Termine sur une note émotionnelle forte et motivante
   - Une phrase finale mémorable qui résume l'essence du livre

EXIGENCES STRICTES :
- Style : {ebook['tone']}, adapté à {', '.join(ebook['target_audience'])}
- ⚠️ INTERDIT : N'utilise JAMAIS les symboles #, ##, ### ou autres balises Markdown
- ⚠️ INTERDIT : Ne répète JAMAIS le mot "Conclusion" dans le texte
- Structure : Utilise UNIQUEMENT le format "🔹 Titre de section" si nécessaire pour des sous-parties
- Ton : Inspirant, optimiste, et orienté vers l'action
- Impact : Crée une fin mémorable qui donne au lecteur l'envie de recommencer sa lecture
- Langage : 100% en français

Réponds UNIQUEMENT avec le texte de la conclusion (le titre "Conclusion" sera ajouté automatiquement)."""

            else:  # chapter
                # Contexte du chapitre précédent pour transitions
                transition_context = ""
                if idx > 0 and previous_chapter_summary:
                    transition_context = f"\n\nLIEN AVEC LE CHAPITRE PRÉCÉDENT :\n{previous_chapter_summary}\n→ Commence par une transition naturelle qui fait le pont entre ces idées."
                
                # Contexte du chapitre suivant
                next_chapter_hint = ""
                if idx < len(data.toc) - 1:
                    next_chap = data.toc[idx + 1]
                    next_chapter_hint = f"\n\nPRÉPARATION POUR LA SUITE :\nLe prochain chapitre abordera : {next_chap['title']}\n→ Termine par une phrase qui crée le lien avec ce sujet."

                prompt = f"""Tu es un auteur professionnel expert en pédagogie et storytelling.

CONTEXTE DU LIVRE :
- Titre : "{ebook['title']}"
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Objectif global : {ebook['description']}

CHAPITRE À RÉDIGER :
Numéro : {chapter['number']}
Titre : {chapter['title']}
Objectif : {chapter['description']}{transition_context}{next_chapter_hint}

MISSION : Rédige un chapitre COMPLET et ENGAGEANT (1200-1800 mots) structuré ainsi :

1. **OUVERTURE** (2-3 paragraphes)
   - Accroche puissante avec question, anecdote ou fait surprenant
   - Annonce claire de ce qui sera couvert dans ce chapitre

2. **DÉVELOPPEMENT EN SECTIONS** (corps principal)
   Organise le contenu en 2-4 sections claires avec :
   - Pour chaque section : un titre descriptif précédé de "🔹" (exemple: "🔹 La première étape vers le changement")
   - Explications claires et approfondies
   - 2-3 exemples concrets et pertinents par section
   - Anecdotes illustratives adaptées au ton {ebook['tone']}
   - Étapes pratiques ou conseils actionnables
   - Analogies ou métaphores pour clarifier les concepts complexes

3. **EN SYNTHÈSE** (section finale OBLIGATOIRE - 1 paragraphe)
   Titre de section : "🔹 En synthèse"
   - Résumé concis des 3-4 points clés du chapitre
   - Le principal enseignement à retenir
   - Lien subtil avec le chapitre suivant

4. **RÉFLEXION PERSONNELLE** (section finale OBLIGATOIRE)
   Titre de section : "🔹 Question de réflexion"
   - 1-2 questions ouvertes qui invitent le lecteur à appliquer ce qu'il a appris
   - Formulation engageante et personnalisée

EXIGENCES STRICTES :
- Style : {ebook['tone']}
- Public : {', '.join(ebook['target_audience'])}
- Structuration : Utilise UNIQUEMENT le format "🔹 Titre de section" pour les sous-parties
- ⚠️ INTERDIT : N'utilise JAMAIS les symboles #, ##, ### ou autres balises Markdown
- ⚠️ INTERDIT : Ne répète JAMAIS le titre principal du chapitre dans le contenu
- Exemples : Minimum 2-3 exemples concrets et situés
- Longueur : Dense et riche, environ 1200-1800 mots
- Langage : 100% en français

Réponds UNIQUEMENT avec le contenu du chapitre (sans le titre principal, il sera ajouté automatiquement)."""

            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"chapter_{data.ebook_id}_{chapter['number']}_{datetime.now(timezone.utc).timestamp()}",
                system_message="Tu es un auteur professionnel expert en création de contenu littéraire de haute qualité."
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(text=prompt)
            content = await chat.send_message(user_message)
            
            chapter_data = {
                "number": chapter["number"],
                "title": chapter["title"],
                "description": chapter["description"],
                "type": chapter_type,
                "content": content.strip(),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            chapters.append(chapter_data)
            
            # Créer un résumé du chapitre pour le chapitre suivant
            if chapter_type == 'chapter':
                previous_chapter_summary = f"Chapitre précédent '{chapter['title']}' : {chapter['description'][:100]}..."
        
        # Update ebook with chapters
        ebooks_collection.update_one(
            {"_id": data.ebook_id},
            {"$set": {
                "chapters": chapters,
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "chapters": chapters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")

class GenerateCoverRequest(BaseModel):
    ebook_id: str

@app.post("/api/ebooks/generate-cover")
async def generate_cover(request: GenerateCoverRequest, current_user = Depends(get_current_user)):
    """Generate a text-based cover page design"""
    try:
        ebook_id = request.ebook_id
        # Get ebook
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Generate cover description/design
        prompt = f"""Tu es un designer de couvertures de livres professionnel.

INFORMATIONS DU LIVRE :
- Titre : {ebook['title']}
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Description : {ebook['description']}

MISSION : Crée une description détaillée de couverture de livre professionnelle qui inclut :

1. **DESIGN VISUEL** :
   - Palette de couleurs recommandée (3-4 couleurs spécifiques)
   - Style graphique (moderne, minimaliste, classique, artistique, etc.)
   - Disposition des éléments (titre, sous-titre, auteur)
   
2. **TYPOGRAPHIE** :
   - Police suggérée pour le titre (avec justification)
   - Taille et style recommandés
   
3. **ÉLÉMENTS GRAPHIQUES** :
   - Icônes, illustrations ou images suggérées
   - Mood et atmosphère visuelle
   
4. **ACCROCHE** :
   - Un sous-titre ou tagline percutant (1 phrase)
   - Une phrase d'accroche pour le dos de couverture

Format de réponse (JSON) :
{{
  "title": "{ebook['title']}",
  "author": "{ebook['author']}",
  "subtitle": "Sous-titre accrocheur ici",
  "design": {{
    "colors": ["#HEX1", "#HEX2", "#HEX3"],
    "style": "description du style",
    "layout": "description de la disposition"
  }},
  "typography": {{
    "title_font": "Nom de la police",
    "style_notes": "Notes sur le style"
  }},
  "graphics": {{
    "suggestions": ["élément 1", "élément 2"],
    "mood": "description de l'atmosphère"
  }},
  "tagline": "Phrase d'accroche percutante",
  "back_cover_text": "Texte pour le dos de couverture (2-3 phrases)"
}}

Réponds UNIQUEMENT avec le JSON."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"cover_{ebook_id}_{datetime.now(timezone.utc).timestamp()}",
            system_message="Tu es un designer professionnel de couvertures de livres."
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Clean and parse response
        import json
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        cover_data = json.loads(clean_response)
        
        # Save cover to ebook
        ebooks_collection.update_one(
            {"_id": ebook_id},
            {"$set": {"cover": cover_data}}
        )
        
        return {
            "success": True,
            "cover": cover_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cover: {str(e)}")

@app.post("/api/ebooks/generate-cover-image")
async def generate_cover_image(request: GenerateCoverRequest, current_user = Depends(get_current_user)):
    """Generate an actual cover image using DALL-E"""
    try:
        ebook_id = request.ebook_id
        # Get ebook
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Create DALL-E prompt for cover image
        dalle_prompt = f"""Professional book cover design for:
Title: "{ebook['title']}"
Author: {ebook['author']}
Genre: {ebook.get('genre', 'Non-fiction')}
Tone: {ebook['tone']}

Design a beautiful, professional book cover with:
- The book title prominently displayed
- Author name
- Modern, eye-catching design
- Color scheme that matches the {ebook['tone']} tone
- High-quality, publishable appearance
- Minimalist and elegant style

No photographs of people. Use abstract designs, patterns, or symbolic imagery.
The design should be professional enough for Amazon KDP or traditional publishing."""

        print(f"Generating cover image with DALL-E for: {ebook['title']}")
        
        # Initialize DALL-E
        image_gen = OpenAIImageGeneration(api_key=EMERGENT_LLM_KEY)
        
        # Generate cover image
        images = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: image_gen.generate_images(
                prompt=dalle_prompt,
                model="gpt-image-1",
                number_of_images=1
            )
        )
        
        if images and len(images) > 0:
            # Convert to base64
            image_base64 = base64.b64encode(images[0]).decode('utf-8')
            
            # Store in GridFS
            image_id = fs.put(
                images[0],
                filename=f"cover_{ebook_id}_{datetime.now(timezone.utc).timestamp()}.png",
                content_type="image/png",
                metadata={
                    "ebook_id": ebook_id,
                    "type": "cover",
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update ebook cover with image
            cover_data = ebook.get('cover', {})
            cover_data['cover_image_base64'] = image_base64
            cover_data['cover_image_id'] = str(image_id)
            
            ebooks_collection.update_one(
                {"_id": ebook_id},
                {"$set": {"cover": cover_data}}
            )
            
            return {
                "success": True,
                "cover_image_base64": image_base64
            }
        else:
            raise HTTPException(status_code=500, detail="No image was generated")
        
    except Exception as e:
        print(f"Error generating cover image: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating cover image: {str(e)}")

@app.post("/api/ebooks/upload-cover-image")
async def upload_cover_image(
    ebook_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload a custom cover image"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, WebP allowed")
        
        # Read file
        image_data = await file.read()
        
        # Store in GridFS
        image_id = fs.put(
            image_data,
            filename=file.filename,
            content_type=file.content_type,
            metadata={
                "ebook_id": ebook_id,
                "type": "cover",
                "uploaded_by": current_user["_id"],
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "source": "user_upload"
            }
        )
        
        # Convert to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Update ebook cover
        cover_data = ebook.get('cover', {})
        cover_data['cover_image_base64'] = image_base64
        cover_data['cover_image_id'] = str(image_id)
        cover_data['source'] = 'user_upload'
        
        ebooks_collection.update_one(
            {"_id": ebook_id},
            {"$set": {"cover": cover_data}}
        )
        
        return {
            "success": True,
            "cover_image_base64": image_base64
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading cover image: {str(e)}")

@app.post("/api/ebooks/create")
async def create_ebook(ebook_data: EbookCreate, current_user = Depends(get_current_user)):
    ebook_id = f"ebook_{datetime.utcnow().timestamp()}".replace(".", "_")
    ebook = {
        "_id": ebook_id,
        "user_id": current_user["_id"],
        "author": ebook_data.author,
        "title": ebook_data.title,
        "tone": ebook_data.tone,
        "target_audience": ebook_data.target_audience,
        "description": ebook_data.description,
        "chapters_count": ebook_data.chapters_count,
        "length": ebook_data.length,
        "genre": ebook_data.genre,
        "about_author": ebook_data.about_author,
        "acknowledgments": ebook_data.acknowledgments,
        "preface": ebook_data.preface,
        "toc": [],
        "chapters": [],
        "status": "draft",
        "created_at": datetime.utcnow().isoformat()
    }
    ebooks_collection.insert_one(ebook)
    
    return {
        "success": True,
        "ebook_id": ebook_id,
        "ebook": ebook
    }

@app.get("/api/ebooks/list")
async def list_ebooks(current_user = Depends(get_current_user)):
    ebooks = list(ebooks_collection.find({"user_id": current_user["_id"]}).sort("created_at", -1))
    return {"ebooks": ebooks}

@app.get("/api/ebooks/{ebook_id}")
async def get_ebook(ebook_id: str, current_user = Depends(get_current_user)):
    ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
    if not ebook:
        raise HTTPException(status_code=404, detail="Ebook not found")
    return ebook

@app.post("/api/ebooks/{ebook_id}/save-toc")
async def save_toc(ebook_id: str, toc_data: dict, current_user = Depends(get_current_user)):
    ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
    if not ebook:
        raise HTTPException(status_code=404, detail="Ebook not found")
    
    ebooks_collection.update_one(
        {"_id": ebook_id},
        {"$set": {"toc": toc_data.get("toc", [])}}
    )
    
    return {"success": True}

class GenerateLegalPagesRequest(BaseModel):
    ebook_id: str
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    edition: Optional[str] = "Première édition"
    year: Optional[int] = None

@app.post("/api/ebooks/generate-legal-pages")
async def generate_legal_pages(request: GenerateLegalPagesRequest, current_user = Depends(get_current_user)):
    """Generate legal pages (copyright, mentions légales, ISBN) for the ebook"""
    try:
        ebook_id = request.ebook_id
        # Get ebook
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Determine year
        year = request.year if request.year else datetime.now(timezone.utc).year
        publisher = request.publisher if request.publisher else "Édition Indépendante"
        
        # Generate legal pages content using AI
        prompt = f"""Tu es un expert juridique et éditorial spécialisé dans la création de pages légales pour les livres.

INFORMATIONS DU LIVRE :
- Titre : {ebook['title']}
- Auteur : {ebook['author']}
- Éditeur : {publisher}
- Année : {year}
- Édition : {request.edition}
- ISBN : {request.isbn if request.isbn else "À attribuer"}

MISSION : Génère les pages légales complètes et professionnelles pour ce livre en français, incluant :

1. **PAGE DE COPYRIGHT**
   - Symbole © avec année et nom de l'auteur
   - Droits de reproduction réservés
   - Mention d'édition
   - ISBN (si fourni)
   - Éditeur
   - Mention du dépôt légal
   
2. **MENTIONS LÉGALES**
   - Protection de la propriété intellectuelle
   - Conditions d'utilisation
   - Avertissement sur la reproduction
   - Contact de l'éditeur/auteur
   
3. **PAGE DE TITRE COMPLÈTE**
   - Titre du livre
   - Nom de l'auteur
   - Éditeur
   - Année

Format de réponse (JSON) :
{{
  "copyright_page": "Texte complet de la page de copyright avec sauts de ligne (\\n)",
  "legal_mentions": "Texte complet des mentions légales avec sauts de ligne (\\n)",
  "title_page": "Texte complet de la page de titre avec sauts de ligne (\\n)",
  "isbn": "{request.isbn if request.isbn else 'Non attribué'}",
  "publisher": "{publisher}",
  "year": {year},
  "edition": "{request.edition}"
}}

EXIGENCES :
- Langage : 100% en français
- Ton : Formel et professionnel
- Conformité : Respecte les standards français et européens
- Lisibilité : Structure claire avec paragraphes distincts

Réponds UNIQUEMENT avec le JSON."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"legal_{ebook_id}_{datetime.now(timezone.utc).timestamp()}",
            system_message="Tu es un expert juridique et éditorial spécialisé dans les pages légales de livres."
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Clean and parse response
        import json
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        legal_data = json.loads(clean_response)
        
        # Save legal pages to ebook
        ebooks_collection.update_one(
            {"_id": ebook_id},
            {"$set": {"legal_pages": legal_data}}
        )
        
        return {
            "success": True,
            "legal_pages": legal_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating legal pages: {str(e)}")

@app.post("/api/ebooks/generate-visual-theme")
async def generate_visual_theme(request: GenerateVisualThemeRequest, current_user = Depends(get_current_user)):
    """Generate visual theme (colors, fonts, styles) for the ebook using AI"""
    try:
        ebook_id = request.ebook_id
        # Get ebook
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Generate theme using AI
        prompt = f"""Tu es un designer graphique expert spécialisé dans la conception de livres numériques et imprimés.

INFORMATIONS DU LIVRE :
- Titre : {ebook['title']}
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Description : {ebook['description']}

MISSION : Crée un thème visuel professionnel et cohérent pour ce livre qui inclut :

1. **PALETTE DE COULEURS**
   - Couleur Primaire : Pour les titres H1, éléments principaux (code HEX)
   - Couleur Secondaire : Pour citations, encadrés, accents (code HEX)
   - Couleur d'Arrière-plan : Pour les encadrés et sections spéciales (code HEX)
   - Justification : Explique pourquoi ces couleurs sont adaptées au sujet

2. **POLICES DE CARACTÈRES**
   - Police pour le Corps : Choisir parmi [Helvetica, Georgia, Arial, Times New Roman, Palatino]
   - Police pour les Titres : Choisir parmi [Helvetica-Bold, Georgia-Bold, Arial-Bold, Times-Bold]
   - Justification : Pourquoi ces polices améliorent la lisibilité

3. **STYLE D'ENCADRÉS/CITATIONS**
   - Type : "classique" (italique + bordure latérale) OU "graphique" (encadré coloré avec icône)
   - Description : Comment appliquer ce style
   - Icône suggérée : (si graphique) emoji ou symbole approprié

4. **SÉPARATEUR DE CHAPITRE**
   - Type : "minimaliste" (simple saut) OU "décoratif" (motif graphique)
   - Description : Si décoratif, décrire le motif (ex: ligne ornementale, symbole)
   - Symbole : (si décoratif) caractère Unicode ou emoji approprié

Format de réponse (JSON strict) :
{{
  "palette": {{
    "primary": "#HEXCODE",
    "secondary": "#HEXCODE",
    "background": "#HEXCODE",
    "justification": "Explication des choix de couleurs..."
  }},
  "fonts": {{
    "body": "Nom de la police",
    "titles": "Nom de la police-Bold",
    "justification": "Explication des choix de polices..."
  }},
  "quote_style": {{
    "type": "classique ou graphique",
    "description": "Description de l'application...",
    "icon": "emoji ou symbole"
  }},
  "chapter_separator": {{
    "type": "minimaliste ou décoratif",
    "description": "Description du séparateur...",
    "symbol": "caractère unicode"
  }},
  "overall_mood": "Description générale de l'ambiance visuelle (1-2 phrases)"
}}

EXIGENCES :
- Couleurs : Codes HEX valides uniquement
- Polices : Choisir uniquement parmi les listes proposées (compatibilité PDF/EPUB)
- Style : Cohérent avec le ton {ebook['tone']} et le public {', '.join(ebook['target_audience'])}
- Professionnel : Le thème doit être élégant et faciliter la lecture
- Langage : Réponse en français

Réponds UNIQUEMENT avec le JSON."""

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"theme_{ebook_id}_{datetime.now(timezone.utc).timestamp()}",
            system_message="Tu es un designer graphique expert spécialisé dans la conception de livres."
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Clean and parse response
        import json
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        theme_data = json.loads(clean_response)
        
        # Save theme to ebook
        ebooks_collection.update_one(
            {"_id": ebook_id},
            {"$set": {"visual_theme": theme_data}}
        )
        
        return {
            "success": True,
            "visual_theme": theme_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating visual theme: {str(e)}")

@app.post("/api/ebooks/generate-illustrations")
async def generate_illustrations(request: GenerateIllustrationsRequest, current_user = Depends(get_current_user)):
    """Generate illustrations for each chapter using AI and DALL-E (OpenAI)"""
    try:
        ebook_id = request.ebook_id
        # Get ebook
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        chapters = ebook.get('chapters', [])
        if not chapters:
            raise HTTPException(status_code=400, detail="Generate content first before illustrations")
        
        # Initialize DALL-E image generator
        image_gen = OpenAIImageGeneration(api_key=EMERGENT_LLM_KEY)
        
        # Generate illustrations for each chapter using AI
        illustrations_data = []
        
        for chapter in chapters:
            chapter_num = chapter.get('number', 0)
            chapter_title = chapter.get('title', '')
            chapter_desc = chapter.get('description', '')
            chapter_content = chapter.get('content', '')[:500]  # First 500 chars for context
            chapter_type = chapter.get('type', 'chapter')
            
            # Skip for introduction/conclusion or limit to regular chapters
            if chapter_type not in ['chapter']:
                continue
            
            # AI generates image prompts for DALL-E
            prompt = f"""Tu es un expert en génération de prompts pour DALL-E (génération d'images IA).

CHAPITRE À ILLUSTRER :
- Numéro : {chapter_num}
- Titre : {chapter_title}
- Description : {chapter_desc}
- Extrait : {chapter_content[:200]}...
- Livre : {ebook['title']} (Ton: {ebook['tone']})

MISSION : Génère 1-2 prompts DALL-E en ANGLAIS pour créer des illustrations qui :
1. **Reflètent visuellement** le contenu et l'émotion du chapitre
2. **Sont artistiques** et esthétiquement agréables (style photo réaliste, illustration digitale, art conceptuel)
3. **Conviennent à un ebook** (pas de texte dans l'image, composition équilibrée)
4. **Restent appropriées** au ton {ebook['tone']} et au public cible

Pour chaque prompt, fournis aussi une description ALT en français pour l'accessibilité.

Format de réponse (JSON strict) :
{{
  "chapter_number": {chapter_num},
  "images": [
    {{
      "dalle_prompt": "Detailed English prompt for DALL-E (ex: A serene landscape showing meditation in nature, soft lighting, peaceful atmosphere, digital art style)",
      "alt_text": "Description accessible en français (ex: Paysage serein montrant une personne en méditation dans la nature)",
      "placement": "Suggestion de placement (ex: Au début du chapitre, Après la section principale)"
    }}
  ]
}}

CONTRAINTES CRITIQUES :
- Maximum 2 images par chapitre (DALL-E est coûteux)
- Prompts en ANGLAIS, détaillés et descriptifs (50-100 mots)
- Alt text en FRANÇAIS, accessible
- Style cohérent avec le thème du livre
- PAS de texte/mots dans les images générées
- Mentionner le style artistique souhaité (photo, illustration, art digital, etc.)

Réponds UNIQUEMENT avec le JSON."""

            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"illust_{ebook_id}_{chapter_num}_{datetime.now(timezone.utc).timestamp()}",
                system_message="Tu es un expert en génération de prompts pour DALL-E et illustration de contenu."
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse AI response
            import json
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            chapter_illust = json.loads(clean_response)
            
            # Generate images with DALL-E for each prompt
            for image_item in chapter_illust.get('images', []):
                dalle_prompt = image_item.get('dalle_prompt', '')
                
                try:
                    # Generate image with DALL-E
                    print(f"Generating DALL-E image for chapter {chapter_num} with prompt: {dalle_prompt[:100]}...")
                    
                    # Use sync call wrapped in executor to avoid async issues
                    images = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: image_gen.generate_images(
                            prompt=dalle_prompt,
                            model="gpt-image-1",
                            number_of_images=1
                        )
                    )
                    
                    print(f"DALL-E response received, images count: {len(images) if images else 0}")
                    
                    if images and len(images) > 0:
                        # Convert image bytes to base64
                        image_base64 = base64.b64encode(images[0]).decode('utf-8')
                        
                        # Store image in GridFS
                        image_id = fs.put(
                            images[0],
                            filename=f"ebook_{ebook_id}_ch{chapter_num}_{datetime.now(timezone.utc).timestamp()}.png",
                            content_type="image/png",
                            metadata={
                                "ebook_id": ebook_id,
                                "chapter_number": chapter_num,
                                "dalle_prompt": dalle_prompt,
                                "generated_at": datetime.now(timezone.utc).isoformat()
                            }
                        )
                        
                        # Add to image item
                        image_item['image_base64'] = image_base64
                        image_item['image_id'] = str(image_id)
                        image_item['image_source'] = 'dall-e'
                        
                        print(f"Image successfully generated and stored for chapter {chapter_num}")
                        
                    else:
                        error_msg = "No image was generated by DALL-E"
                        print(f"ERROR: {error_msg}")
                        image_item['error'] = error_msg
                        
                except Exception as img_error:
                    error_msg = f"Error generating DALL-E image: {str(img_error)}"
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    image_item['error'] = str(img_error)
            
            illustrations_data.append(chapter_illust)
        
        # Save illustrations to ebook
        ebooks_collection.update_one(
            {"_id": ebook_id},
            {"$set": {"illustrations": illustrations_data}}
        )
        
        return {
            "success": True,
            "illustrations": illustrations_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating illustrations: {str(e)}")

@app.post("/api/ebooks/edit-chapter")
async def edit_chapter(request: EditChapterRequest, current_user = Depends(get_current_user)):
    """Edit chapter content manually"""
    try:
        ebook = ebooks_collection.find_one({"_id": request.ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        chapters = ebook.get('chapters', [])
        chapter_found = False
        
        for chapter in chapters:
            if chapter.get('number') == request.chapter_number:
                chapter['content'] = request.new_content
                chapter['edited_at'] = datetime.now(timezone.utc).isoformat()
                chapter_found = True
                break
        
        if not chapter_found:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Update ebook
        ebooks_collection.update_one(
            {"_id": request.ebook_id},
            {"$set": {"chapters": chapters}}
        )
        
        return {
            "success": True,
            "message": "Chapter updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error editing chapter: {str(e)}")

@app.post("/api/ebooks/regenerate-chapter")
async def regenerate_chapter(request: RegenerateChapterRequest, current_user = Depends(get_current_user)):
    """Regenerate a specific chapter using AI"""
    try:
        ebook = ebooks_collection.find_one({"_id": request.ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        chapters = ebook.get('chapters', [])
        chapter_to_regen = None
        chapter_index = -1
        
        for idx, chapter in enumerate(chapters):
            if chapter.get('number') == request.chapter_number:
                chapter_to_regen = chapter
                chapter_index = idx
                break
        
        if not chapter_to_regen:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Regenerate content using same logic as original generation
        chapter_type = chapter_to_regen.get('type', 'chapter')
        
        if chapter_type == 'chapter':
            prompt = f"""Tu es un auteur professionnel expert en pédagogie et storytelling.

CONTEXTE DU LIVRE :
- Titre : "{ebook['title']}"
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Objectif global : {ebook['description']}

CHAPITRE À RÉGÉNÉRER :
Numéro : {chapter_to_regen['number']}
Titre : {chapter_to_regen['title']}
Objectif : {chapter_to_regen.get('description', 'Développer ce thème')}

MISSION : Rédige un chapitre COMPLET et ENGAGEANT (1200-1800 mots) structuré ainsi :

1. **OUVERTURE** (2-3 paragraphes)
   - Accroche puissante
   - Annonce claire du contenu

2. **DÉVELOPPEMENT EN SECTIONS** (corps principal)
   - 2-4 sections claires avec titre "🔹 Titre"
   - Explications approfondies
   - 2-3 exemples concrets par section
   - Anecdotes illustratives

3. **EN SYNTHÈSE** (section finale OBLIGATOIRE)
   "🔹 En synthèse"
   - Résumé des 3-4 points clés
   - Principal enseignement

4. **RÉFLEXION PERSONNELLE** (section finale OBLIGATOIRE)
   "🔹 Question de réflexion"
   - 1-2 questions ouvertes

EXIGENCES STRICTES :
- Style : {ebook['tone']}
- ⚠️ INTERDIT : N'utilise JAMAIS #, ##, ### 
- ⚠️ INTERDIT : Ne répète JAMAIS le titre du chapitre
- Format : "🔹 Titre" pour sous-sections
- Langage : 100% français

Réponds UNIQUEMENT avec le contenu."""

        else:
            # For introduction or conclusion, use appropriate prompt
            prompt = f"""Régénère le contenu pour ce type de chapitre: {chapter_type}"""
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"regen_{request.ebook_id}_{request.chapter_number}_{datetime.now(timezone.utc).timestamp()}",
            system_message="Tu es un auteur professionnel."
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=prompt)
        new_content = await chat.send_message(user_message)
        
        # Update chapter
        chapters[chapter_index]['content'] = new_content.strip()
        chapters[chapter_index]['regenerated_at'] = datetime.now(timezone.utc).isoformat()
        
        ebooks_collection.update_one(
            {"_id": request.ebook_id},
            {"$set": {"chapters": chapters}}
        )
        
        return {
            "success": True,
            "new_content": new_content.strip()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating chapter: {str(e)}")

@app.post("/api/ebooks/regenerate-image")
async def regenerate_image(request: RegenerateImageRequest, current_user = Depends(get_current_user)):
    """Regenerate a specific illustration using DALL-E"""
    try:
        ebook = ebooks_collection.find_one({"_id": request.ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        illustrations = ebook.get('illustrations', [])
        
        # Find the chapter illustration
        chapter_illust = None
        for illust in illustrations:
            if illust.get('chapter_number') == request.chapter_number:
                chapter_illust = illust
                break
        
        if not chapter_illust:
            raise HTTPException(status_code=404, detail="Illustrations for this chapter not found")
        
        images = chapter_illust.get('images', [])
        if request.illustration_index >= len(images):
            raise HTTPException(status_code=404, detail="Illustration index out of range")
        
        image_item = images[request.illustration_index]
        dalle_prompt = image_item.get('dalle_prompt', '')
        
        # Regenerate with DALL-E
        image_gen = OpenAIImageGeneration(api_key=EMERGENT_LLM_KEY)
        
        generated_images = await image_gen.generate_images(
            prompt=dalle_prompt,
            model="gpt-image-1",
            number_of_images=1
        )
        
        if generated_images and len(generated_images) > 0:
            # Convert to base64
            image_base64 = base64.b64encode(generated_images[0]).decode('utf-8')
            
            # Store in GridFS
            image_id = fs.put(
                generated_images[0],
                filename=f"ebook_{request.ebook_id}_ch{request.chapter_number}_regen_{datetime.now(timezone.utc).timestamp()}.png",
                content_type="image/png",
                metadata={
                    "ebook_id": request.ebook_id,
                    "chapter_number": request.chapter_number,
                    "dalle_prompt": dalle_prompt,
                    "regenerated_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update image item
            image_item['image_base64'] = image_base64
            image_item['image_id'] = str(image_id)
            image_item['regenerated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Save back to database
            ebooks_collection.update_one(
                {"_id": request.ebook_id},
                {"$set": {"illustrations": illustrations}}
            )
            
            return {
                "success": True,
                "image_base64": image_base64
            }
        else:
            raise HTTPException(status_code=500, detail="No image was generated")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating image: {str(e)}")

@app.post("/api/ebooks/upload-custom-image")
async def upload_custom_image(
    ebook_id: str,
    chapter_number: int,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload a custom image for a chapter"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, WebP allowed")
        
        # Read file
        image_data = await file.read()
        
        # Store in GridFS
        image_id = fs.put(
            image_data,
            filename=file.filename,
            content_type=file.content_type,
            metadata={
                "ebook_id": ebook_id,
                "chapter_number": chapter_number,
                "uploaded_by": current_user["_id"],
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "source": "user_upload"
            }
        )
        
        # Convert to base64 for frontend
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Add to illustrations array
        illustrations = ebook.get('illustrations', [])
        
        # Find or create chapter illustrations entry
        chapter_found = False
        for illust in illustrations:
            if illust.get('chapter_number') == chapter_number:
                if 'images' not in illust:
                    illust['images'] = []
                illust['images'].append({
                    'image_base64': image_base64,
                    'image_id': str(image_id),
                    'image_source': 'user_upload',
                    'alt_text': f"Image personnalisée pour le chapitre {chapter_number}",
                    'placement': "Personnalisée par l'utilisateur"
                })
                chapter_found = True
                break
        
        if not chapter_found:
            illustrations.append({
                'chapter_number': chapter_number,
                'images': [{
                    'image_base64': image_base64,
                    'image_id': str(image_id),
                    'image_source': 'user_upload',
                    'alt_text': f"Image personnalisée pour le chapitre {chapter_number}",
                    'placement': "Personnalisée par l'utilisateur"
                }]
            })
        
        ebooks_collection.update_one(
            {"_id": ebook_id},
            {"$set": {"illustrations": illustrations}}
        )
        
        return {
            "success": True,
            "image_base64": image_base64,
            "image_id": str(image_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

# Export Routes
@app.get("/api/ebooks/{ebook_id}/export/pdf")
async def export_pdf(ebook_id: str, current_user = Depends(get_current_user)):
    """Export ebook to PDF format"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        exporter = EbookExporter(ebook)
        pdf_buffer = exporter.export_to_pdf()
        
        filename = f"{ebook['title'].replace(' ', '_')}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting PDF: {str(e)}")

@app.get("/api/ebooks/{ebook_id}/export/epub")
async def export_epub(ebook_id: str, current_user = Depends(get_current_user)):
    """Export ebook to EPUB format (e-readers)"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        exporter = EbookExporter(ebook)
        epub_buffer = exporter.export_to_epub()
        
        filename = f"{ebook['title'].replace(' ', '_')}.epub"
        
        return StreamingResponse(
            epub_buffer,
            media_type="application/epub+zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting EPUB: {str(e)}")

@app.get("/api/ebooks/{ebook_id}/export/docx")
async def export_docx(ebook_id: str, current_user = Depends(get_current_user)):
    """Export ebook to DOCX format (editable)"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        exporter = EbookExporter(ebook)
        docx_buffer = exporter.export_to_docx()
        
        filename = f"{ebook['title'].replace(' ', '_')}.docx"
        
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting DOCX: {str(e)}")

@app.get("/api/ebooks/{ebook_id}/export/html")
async def export_html(ebook_id: str, current_user = Depends(get_current_user)):
    """Export ebook to HTML format (interactive flipbook)"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        exporter = EbookExporter(ebook)
        html_buffer = exporter.export_to_html_flipbook()
        
        filename = f"{ebook['title'].replace(' ', '_')}_flipbook.html"
        
        return StreamingResponse(
            html_buffer,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting HTML: {str(e)}")

@app.get("/api/ebooks/{ebook_id}/export/mobi")
async def export_mobi(ebook_id: str, current_user = Depends(get_current_user)):
    """Export ebook to MOBI format (Kindle)"""
    try:
        ebook = ebooks_collection.find_one({"_id": ebook_id, "user_id": current_user["_id"]})
        if not ebook:
            raise HTTPException(status_code=404, detail="Ebook not found")
        
        # Note: MOBI requires conversion tool
        # For now, return EPUB (can be converted to MOBI using Calibre)
        exporter = EbookExporter(ebook)
        epub_buffer = exporter.export_to_mobi()
        
        filename = f"{ebook['title'].replace(' ', '_')}_for_kindle.epub"
        
        return StreamingResponse(
            epub_buffer,
            media_type="application/epub+zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Note": "Convert this EPUB to MOBI using Calibre or send to Kindle email"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting MOBI: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)