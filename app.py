from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

app = FastAPI()

# ------------------------------------------------------------------
# CONFIGURACIÓN DE BASE DE DATOS (SQLite)
# ------------------------------------------------------------------
DATABASE_URL = "sqlite:///./detecworm.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de Usuario en BD
class UsuarioBD(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String, unique=True, index=True) # ID único de Google
    email = Column(String, unique=True)
    nombre = Column(String)
    foto = Column(String)
    
    # Relación con sus consultas
    consultas = relationship("ConsultaBD", back_populates="usuario")

# Modelo de Consultas de Cultivos
class ConsultaBD(Base):
    __tablename__ = "consultas"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    cultivo = Column(String, default="General")
    diagnostico = Column(String) # Nombre de la plaga / enfermedad / estado
    confianza = Column(Float)   # Porcentaje de certeza (ej. 98.5)
    fecha = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("UsuarioBD", back_populates="consultas")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------
# MIDDLEWARE Y TEMPLATES
# ------------------------------------------------------------------
app.add_middleware(SessionMiddleware, secret_key="detecworm_super_secret_key_2026")
templates = Jinja2Templates(directory="templates")

GOOGLE_CLIENT_ID = "857174676804-8qj3u5ph6ut9drjar4rq2dis0mf6ctiq.apps.googleusercontent.com"

# Endpoint ligero para el Cronjob (Keep-Alive)
@app.get("/ping")
async def ping():
    return {"status": "ok"}

# ------------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN
# ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.get("/login", response_class=HTMLResponse)
async def read_login(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/auth/google")
async def auth_google(request: Request):
    data = await request.json()
    token = data.get("token")
    
    try:
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60
        )
        
        user_data = {
            "sub": idinfo.get("sub"),
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture")
        }
        
        # Guardar/Verificar usuario en BD
        db = SessionLocal()
        usuario_db = db.query(UsuarioBD).filter(UsuarioBD.google_sub == user_data["sub"]).first()
        if not usuario_db:
            usuario_db = UsuarioBD(
                google_sub=user_data["sub"],
                email=user_data["email"],
                nombre=user_data["name"],
                foto=user_data["picture"]
            )
            db.add(usuario_db)
            db.commit()
            db.refresh(usuario_db)
        
        # Guardamos el ID interno de la BD en la sesión
        user_data["id"] = usuario_db.id
        db.close()
        
        request.session["user"] = user_data
        return {"status": "success", "user": user_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token inválido: {str(e)}")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# ------------------------------------------------------------------
# RUTAS DE HISTORIAL Y PERFIL
# ------------------------------------------------------------------
@app.get("/perfil", response_class=HTMLResponse)
async def ver_perfil(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    
    db = SessionLocal()
    # Obtener las consultas del usuario ordenadas de la más reciente a la más antigua
    consultas = db.query(ConsultaBD).filter(ConsultaBD.usuario_id == user["id"]).order_by(ConsultaBD.fecha.desc()).all()
    db.close()
    
    return templates.TemplateResponse(
        request=request, 
        name="perfil.html", 
        context={"user": user, "consultas": consultas}
    )

@app.post("/guardar-consulta")
async def guardar_consulta(
    request: Request, 
    diagnostico: str = Form(...), 
    confianza: float = Form(...), 
    cultivo: str = Form("General")
):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    db = SessionLocal()
    nueva_consulta = ConsultaBD(
        usuario_id=user["id"],
        cultivo=cultivo,
        diagnostico=diagnostico,
        confianza=confianza
    )
    db.add(nueva_consulta)
    db.commit()
    db.refresh(nueva_consulta)
    db.close()
    
    return {"status": "success", "message": "Consulta registrada correctamente"}

@app.delete("/eliminar-consulta/{consulta_id}")
async def eliminar_consulta(consulta_id: int, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    
    db = SessionLocal()
    # Buscamos la consulta asegurándonos de que le pertenezca al usuario en sesión
    consulta = db.query(ConsultaBD).filter(
        ConsultaBD.id == consulta_id, 
        ConsultaBD.usuario_id == user["id"]
    ).first()
    
    if not consulta:
        db.close()
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    db.delete(consulta)
    db.commit()
    db.close()
    
    return {"status": "success", "message": "Registro eliminado correctamente"}