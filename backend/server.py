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
        # Create prompt for TOC generation
        prompt = f"""Tu es un expert en création de livres et structuration de contenu.

Génère une table des matières détaillée pour un ebook avec les caractéristiques suivantes :

Titre : {data.title}
Auteur : {data.author}
Ton : {data.tone}
Public cible : {', '.join(data.target_audience)}
Description : {data.description}
Nombre de chapitres : {data.chapters_count}
Longueur approximative : {data.length}

Crée une table des matières structurée avec exactement {data.chapters_count} chapitres.
Chaque chapitre doit avoir :
- Un numéro (1, 2, 3...)
- Un titre accrocheur et pertinent
- Une brève description (2-3 phrases) de ce qui sera couvert

Réponds UNIQUEMENT avec un JSON valide dans ce format exact :
{{
  "chapters": [
    {{
      "number": 1,
      "title": "Titre du chapitre",
      "description": "Description du contenu du chapitre"
    }}
  ]
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

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
        
        for chapter in data.toc:
            prompt = f"""Tu es un auteur professionnel de livres.

Rédige le contenu complet du chapitre suivant pour l'ebook "{ebook['title']}" :

Chapitre {chapter['number']} : {chapter['title']}
Description : {chapter['description']}

Caractéristiques du livre :
- Auteur : {ebook['author']}
- Ton : {ebook['tone']}
- Public cible : {', '.join(ebook['target_audience'])}
- Contexte : {ebook['description']}
- Longueur : {ebook['length']}

Rédige un contenu riche et engageant d'environ 800-1200 mots pour ce chapitre.
Utilise un style {ebook['tone']} adapté à {', '.join(ebook['target_audience'])}.
Inclus des exemples concrets, des transitions fluides et une conclusion.

Réponds UNIQUEMENT avec le contenu du chapitre, sans titre ni numéro de chapitre (juste le texte)."""

            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"chapter_{data.ebook_id}_{chapter['number']}_{datetime.utcnow().timestamp()}",
                system_message="Tu es un auteur professionnel expert en création de contenu littéraire de qualité."
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(text=prompt)
            content = await chat.send_message(user_message)
            
            chapter_data = {
                "number": chapter["number"],
                "title": chapter["title"],
                "description": chapter["description"],
                "content": content.strip(),
                "generated_at": datetime.utcnow().isoformat()
            }
            chapters.append(chapter_data)
        
        # Update ebook with chapters
        ebooks_collection.update_one(
            {"_id": data.ebook_id},
            {"$set": {
                "chapters": chapters,
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            }}
        )
        
        return {
            "success": True,
            "chapters": chapters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {str(e)}")

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