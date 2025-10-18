from fastapi import FastAPI, HTTPException, Depends, status, Response, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import asyncio
import httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()

app = FastAPI(title="YooCreat API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:8001",
        "https://ebook-factory-15.preview.emergentagent.com",
        "https://*.preview.emergentagent.com"
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
Crée une structure de livre COHÉRENTE et PROFESSIONNELLE avec :
1. Une INTRODUCTION captivante (chapitre 0)
2. {data.chapters_count} chapitres de contenu principal (numérotés 1 à {data.chapters_count})
3. Une CONCLUSION percutante (dernier chapitre)

EXIGENCES pour chaque élément :
- Numéro : 0 pour intro, 1-{data.chapters_count} pour chapitres, {data.chapters_count + 1} pour conclusion
- Titre : Accrocheur, pertinent, adapté au ton {data.tone}
- Description : 2-3 phrases décrivant le contenu et la progression logique
- Assure une PROGRESSION NATURELLE d'un chapitre à l'autre
- Intègre des TRANSITIONS conceptuelles entre chapitres

Réponds UNIQUEMENT avec ce JSON valide (sans markdown, sans texte avant/après) :
{{
  "chapters": [
    {{
      "number": 0,
      "title": "Introduction",
      "description": "Accroche le lecteur, présente le sujet et annonce les bénéfices",
      "type": "introduction"
    }},
    {{
      "number": 1,
      "title": "Premier chapitre...",
      "description": "Description détaillée...",
      "type": "chapter"
    }},
    ...
    {{
      "number": {data.chapters_count + 1},
      "title": "Conclusion",
      "description": "Synthèse, call-to-action et ouverture",
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

MISSION : Rédige une INTRODUCTION percutante (800-1000 mots) qui :
1. **ACCROCHE** le lecteur dès les premières lignes
2. **PRÉSENTE** le problème ou sujet principal
3. **EXPLIQUE** pourquoi ce livre est important pour le lecteur
4. **ANNONCE** les bénéfices et ce qu'il va apprendre
5. **CRÉE** l'anticipation pour la suite

Style : {ebook['tone']}, adapté à {', '.join(ebook['target_audience'])}.

Utilise :
- Une anecdote personnelle ou une statistique marquante pour démarrer
- Des questions qui interpellent le lecteur
- Des promesses concrètes

Réponds UNIQUEMENT avec le texte de l'introduction (sans titre)."""

            elif chapter_type == 'conclusion':
                prompt = f"""Tu es un auteur professionnel spécialisé en conclusions mémorables.

CONTEXTE DU LIVRE :
- Titre : "{ebook['title']}"
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Parcours du livre : {ebook['description']}

MISSION : Rédige une CONCLUSION puissante (700-900 mots) qui :
1. **SYNTHÉTISE** les points clés abordés dans le livre
2. **RENFORCE** le message principal
3. **INSPIRE** le lecteur à agir
4. **DONNE** des prochaines étapes concrètes
5. **TERMINE** sur une note mémorable et motivante

Style : {ebook['tone']}, adapté à {', '.join(ebook['target_audience'])}.

Inclus :
- Un rappel des transformations promises
- Un call-to-action clair
- Une ouverture vers l'avenir

Réponds UNIQUEMENT avec le texte de la conclusion (sans titre)."""

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

MISSION : Rédige un chapitre COMPLET et ENGAGEANT (1000-1500 mots) qui :

1. **INTRODUCTION DU CHAPITRE** (1-2 paragraphes)
   - Accroche avec une question, anecdote ou fait surprenant
   - Annonce ce qui sera couvert

2. **DÉVELOPPEMENT** (corps principal)
   - Explications claires et structurées
   - 2-3 exemples concrets et pertinents
   - Anecdotes illustratives selon le ton {ebook['tone']}
   - Étapes pratiques ou points détaillés
   - Analogies si nécessaire pour clarifier

3. **CONCLUSION DU CHAPITRE** (1 paragraphe)
   - Résumé des points essentiels
   - Takeaway principal
   - Connexion naturelle vers le chapitre suivant

EXIGENCES :
- Style : {ebook['tone']}
- Public : {', '.join(ebook['target_audience'])}
- Structure : Utilise des sous-titres internes (##) pour organiser
- Exemples : Minimum 2 exemples concrets
- Longueur : Dense et riche, environ 1000-1500 mots

Réponds UNIQUEMENT avec le contenu du chapitre (sans répéter le titre principal)."""

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

@app.post("/api/ebooks/generate-cover")
async def generate_cover(ebook_id: str, current_user = Depends(get_current_user)):
    """Generate a text-based cover page design"""
    try:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)