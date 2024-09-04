from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.future import select
from pydantic import BaseModel, Field
from trycourier import Courier
from typing import List, Dict

# Configuration de la base de données
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèle de données pour les capteurs
class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    water_level = Column(Float, nullable=False)
    caustic_soda_level = Column(Float, nullable=False)
    water_temperature = Column(Float, nullable=False)
    caustic_soda_temperature = Column(Float, nullable=False)
    voltage = Column(Float, nullable=False)

# Modèle de données pour les utilisateurs
class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)

# Création des tables
Base.metadata.create_all(bind=engine)

# Schéma de validation des données d'entrée pour les capteurs
class SensorDataCreate(BaseModel):
    water_level: float = Field(..., example=85.0)
    caustic_soda_level: float = Field(..., example=1.5)
    water_temperature: float = Field(..., example=50.0)
    caustic_soda_temperature: float = Field(..., example=60.0)
    voltage: float = Field(..., example=320.0)

# Schéma de validation pour les rôles des utilisateurs
class UserRoleCreate(BaseModel):
    email: str
    role: str

# Application FastAPI
app = FastAPI()

# Ajout de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Changez cela pour spécifier les origines permises
    allow_credentials=True,
    allow_methods=["*"],  # Ou spécifiez les méthodes autorisées
    allow_headers=["*"],  # Ou spécifiez les en-têtes autorisés
)

# Dépendance pour obtenir la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dictionnaire des rôles associés aux paramètres
roles_dict = {
    "water_level": ["technicien", "admin"],
    "caustic_soda_level": ["technicien", "admin"],
    "water_temperature": ["technicien", "admin"],
    "caustic_soda_temperature": ["technicien", "admin"],
    "voltage": ["électricien", "admin"]
}

# Fonction pour envoyer une notification
def envoyer_notification(param, valeur, destinataires):
    client = Courier(auth_token="dk_prod_PZXXPRD2JX4Z38QBA44X2804SXWA")

    # Dictionnaire des événements associés aux paramètres
    evenements = {
        "water_level": "2G86E4KDHMMBHXGXJXBF6573MBZW",
        "water_temperature": "FP811B8W2FM2JGMY2SEJK3Y9MT25",
        "caustic_soda_level": "3PX4DMN3M6MRTTJ8ARXPRQQFZC9S",
        "caustic_soda_temperature": "ZVPEQH7T3HM9JZM0VPMPCSRA9502",
        "voltage": "AD61BAKR4F4T4CPWS3P7EV7QMMM1"
    }

    event_id = evenements.get(param)

    if not event_id:
        print(f"Événement non trouvé pour {param}.")
        return

    for email in destinataires:
        client.send(
            event=event_id,
            recipient=email,
            profile={
                "email": email
            },
            data={
                "param": param,
                "valeur": valeur
            }
        )
        print(f"Notification envoyée pour {param} avec une valeur de {valeur}.")

# Fonction pour vérifier les valeurs et envoyer les notifications aux bons utilisateurs
def verifier_valeurs(params: SensorDataCreate, db: Session):
    # Plages normales
    plages_normales = {
        "water_level": (75, 100),
        "caustic_soda_level": (1, 2),
        "water_temperature": (40, 80),
        "caustic_soda_temperature": (40, 80),
        "voltage": (10, 14)
    }

    # Vérification des valeurs
    for param, plage in plages_normales.items():
        valeur = getattr(params, param)
        if not (plage[0] <= valeur <= plage[1]):
            # Obtenir les destinataires en fonction des rôles associés au paramètre
            destinataires = db.execute(select(UserRole.email).where(UserRole.role.in_(roles_dict.get(param, [])))).scalars().all()
            envoyer_notification(param, valeur, destinataires)
            print(f"Valeur critique trouvée : {param} est critique avec une valeur de {valeur}.")

# Route pour recevoir et vérifier les données
@app.post("/verifier")
def verifier_donnees(params: SensorDataCreate, db: Session = Depends(get_db)):
    verifier_valeurs(params, db)
    db_data = SensorData(**params.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return {"message": "Vérification terminée."}

# Route pour obtenir toutes les données des capteurs
@app.get("/sensor_data", response_model=List[SensorDataCreate])
def lire_donnees(db: Session = Depends(get_db)):
    result = db.execute(select(SensorData))
    sensor_data = result.scalars().all()
    return sensor_data

# Nouveau endpoint pour créer les utilisateurs avec leur rôle
@app.post("/create_user_role")
def create_user_role(user: UserRoleCreate, db: Session = Depends(get_db)):
    db_user = UserRole(email=user.email, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Notification à l'utilisateur nouvellement ajouté
    envoyer_notification("new_user", "Vous avez été ajouté en tant que " + user.role, [user.email])
    
    return {"message": "Utilisateur ajouté avec succès.", "user": {"email": user.email, "role": user.role}}

# Route pour obtenir tous les utilisateurs et leurs rôles
@app.get("/user_roles", response_model=List[UserRoleCreate])
def lire_utilisateurs(db: Session = Depends(get_db)):
    result = db.execute(select(UserRole))
    users = result.scalars().all()
    return [{"email": user.email, "role": user.role} for user in users]
