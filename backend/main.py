import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./reve_damour.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    age = Column(Integer)
    pays = Column(String)
    biographie = Column(Text)
    passions = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Le Rêve d'Amour API",
    description="Backend de l'application de rencontre mondiale",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client()

class UserProfile(BaseModel):
    nom: str
    age: int
    pays: str
    biographie: str
    passions: list[str]

class IceBreakerRequest(BaseModel):
    user_profil: UserProfile
    match_profil: UserProfile

class TranslateRequest(BaseModel):
    message: str
    langue_cible: str

@app.post("/api/utilisateurs/inscription")
async def inscrire_utilisateur(profil: UserProfile):
    db = SessionLocal()
    try:
        db_user = UserDB(
            nom=profil.nom,
            age=profil.age,
            pays=profil.pays,
            biographie=profil.biographie,
            passions=",".join(profil.passions)
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"success": True, "message": f"Utilisateur {profil.nom} enregistré avec succès !", "user_id": db_user.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/utilisateurs/tous")
async def lister_utilisateurs():
    db = SessionLocal()
    users = db.query(UserDB).all()
    db.close()
    
    resultat = []
    for u in users:
        resultat.append({
            "id": u.id,
            "nom": u.nom,
            "age": u.age,
            "pays": u.pays,
            "biographie": u.biographie,
            "passions": u.passions.split(",") if u.passions else []
        })
    return resultat

@app.post("/api/cupidon-ia/icebreaker")
async def generer_icebreaker(data: IceBreakerRequest):
    try:
        prompt = f"""
        Tu es Cupidon, l'assistant IA romantique de l'application 'Le Rêve d'Amour'.
        Expéditeur : {data.user_profil.nom} ({data.user_profil.pays}) - Bio : {data.user_profil.biographie}
        Destinataire : {data.match_profil.nom} ({data.match_profil.pays}) - Bio : {data.match_profil.biographie}
        Génère un premier message original, respectueux et charmant, prêt à être envoyé. Donne uniquement le texte.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"success": True, "message_suggere": response.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cupidon-ia/traduire")
async def traduire_message(data: TranslateRequest):
    try:
        prompt = f"Traduis ce message romantique en {data.langue_cible}, en gardant un ton chaleureux : '{data.message}'. Donne uniquement le texte traduit."
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"success": True, "traduction": response.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
