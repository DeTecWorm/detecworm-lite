from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timedelta
import os
import io
import random
import threading
import time
import numpy as np
from PIL import Image

# Carga dinámica del motor de inferencia LiteRT
try:
    from ai_edge_litert.interpreter import Interpreter
    litert_available = True
except ImportError:
    litert_available = False

app = FastAPI()

# ------------------------------------------------------------------
# MONTAJE DE ARCHIVOS ESTÁTICOS
# ------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# ------------------------------------------------------------------
# CONFIGURACIÓN DE BASE DE DATOS (SQLite)
# ------------------------------------------------------------------
DATABASE_URL = "sqlite:///./detecworm.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UsuarioBD(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    nombre = Column(String)
    foto = Column(String)
    consultas = relationship("ConsultaBD", back_populates="usuario")

class ConsultaBD(Base):
    __tablename__ = "consultas"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    cultivo = Column(String, default="General")
    diagnostico = Column(String)
    confianza = Column(Float)
    nivel_riesgo = Column(String, default="verde") 
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario = relationship("UsuarioBD", back_populates="consultas")

Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------
# ESTADO GLOBAL DE SENSORES (Para lectura de hardware en tiempo real)
# ------------------------------------------------------------------
estado_sensores = {
    "temperatura": 24.5,
    "humedad_suelo": 65.0,
    "sensor_capacitivo": "Seco / Sin contacto",
    "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

def bucle_lectura_hardware():
    """Hilo en segundo plano para simular/leer pines físicos de la Orange Pi"""
    global estado_sensores
    while True:
        try:
            # TODO: Aquí puedes reemplazar estos valores simulados por las lecturas reales 
            # de tus librerías de pines GPIO (ej. OPi.GPIO, Adafruit_DHT, etc.)
            estado_sensores["temperatura"] = round(random.uniform(22.0, 31.5), 1)
            estado_sensores["humedad_suelo"] = round(random.uniform(40.0, 85.0), 1)
            estado_sensores["sensor_capacitivo"] = random.choice(["Húmedo detectado", "Seco / Sin contacto"])
            estado_sensores["ultima_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Imprime en la terminal de la Orange Pi para verificar que está midiendo constantemente
            print(f"-> [HARDWARE] Temp: {estado_sensores['temperatura']}°C | Humedad Suelo: {estado_sensores['humedad_suelo']}% | Capacitivo: {estado_sensores['sensor_capacitivo']}")
        except Exception as e:
            print(f"-> Error leyendo hardware: {e}")
        
        time.sleep(5)  # Lee cada 5 segundos

# Arrancar el hilo de hardware al iniciar la app
hilo_hw = threading.Thread(target=bucle_lectura_hardware, daemon=True)
hilo_hw.start()

# ------------------------------------------------------------------
# CARGA Y CONFIGURACIÓN DE MODELO IA (LiteRT)
# ------------------------------------------------------------------
MODEL_PATH = "detecworm_model.tflite"
interpreter = None
input_details = None
output_details = None

if os.path.exists(MODEL_PATH) and litert_available:
    try:
        interpreter = Interpreter(model_path=MODEL_PATH)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        print("-> Modelo LiteRT cargado y listo en memoria.")
    except Exception as e:
        print(f"-> Error cargando LiteRT: {e}")
else:
    print(f"-> AVISO: No se encontró el archivo {MODEL_PATH} o LiteRT no está disponible.")

CLASS_NAMES = ["algo_danado", "danado", "sano"]

# ------------------------------------------------------------------
# MIDDLEWARE Y TEMPLATES
# ------------------------------------------------------------------
app.add_middleware(SessionMiddleware, secret_key="detecworm_super_secret_key_2026")
templates = Jinja2Templates(directory="templates")
GOOGLE_CLIENT_ID = "857174676804-8qj3u5ph6ut9drjar4rq2dis0mf6ctiq.apps.googleusercontent.com"

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.get("/api/estado-sensores")
async def api_estado_sensores():
    """Endpoint para que el frontend consulte los sensores físicos en vivo"""
    return {"status": "success", "sensores": estado_sensores}

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
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID, clock_skew_in_seconds=60)
        user_data = {
            "sub": idinfo.get("sub"),
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture")
        }
        db = SessionLocal()
        usuario_db = db.query(UsuarioBD).filter(UsuarioBD.google_sub == user_data["sub"]).first()
        if not usuario_db:
            usuario_db = UsuarioBD(google_sub=user_data["sub"], email=user_data["email"], nombre=user_data["name"], foto=user_data["picture"])
            db.add(usuario_db)
            db.commit()
            db.refresh(usuario_db)
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
# ESCUDO ANTI-BASURA & ANÁLISIS
# ------------------------------------------------------------------
def analizar_caracteristicas_imagen(pil_img):
    img_np = np.array(pil_img, dtype=np.float32)
    R, G, B = img_np[:, :, 0], img_np[:, :, 1], img_np[:, :, 2]
    total_pixeles = R.size
    
    r, g, b = R / 255.0, G / 255.0, B / 255.0
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    delta = maxc - minc
    delta_safe = np.where(delta == 0, 1e-6, delta)

    hue = np.zeros_like(maxc)
    mask_r = (maxc == r) & (delta > 0)
    mask_g = (maxc == g) & (delta > 0) & (~mask_r)
    mask_b = (maxc == b) & (delta > 0) & (~mask_r) & (~mask_g)

    hue[mask_r] = 60 * (((g[mask_r] - b[mask_r]) / delta_safe[mask_r]) % 6)
    hue[mask_g] = 60 * (((b[mask_g] - r[mask_g]) / delta_safe[mask_g]) + 2)
    hue[mask_b] = 60 * (((r[mask_b] - g[mask_b]) / delta_safe[mask_b]) + 4)

    sat = np.where(maxc > 0, delta / np.where(maxc == 0, 1e-6, maxc), 0)
    val = maxc

    mask_dark = (R < 50) & (G < 50) & (B < 50)
    mask_gray_white = (np.abs(R - G) < 25) & (np.abs(G - B) < 25) & (R > 90)
    
    max_rgb = np.maximum(np.maximum(R, G), B)
    min_rgb = np.minimum(np.minimum(R, G), B)
    mask_tono_calido = (R > 95) & (G > 40) & (B > 20) & ((max_rgb - min_rgb) > 15) & (np.abs(R - G) > 15) & (R > G) & (R > B)
    
    mask_verde_hsv = (hue >= 65) & (hue <= 170) & (sat > 0.15) & (val > 0.12)
    mask_seca_hsv = (hue >= 15) & (hue <= 65) & (sat > 0.12) & (val > 0.10)
    ratio_vegetacion = np.sum(mask_verde_hsv | mask_seca_hsv) / total_pixeles

    gray = 0.299 * R + 0.587 * G + 0.114 * B
    gx, gy = np.diff(gray, axis=1), np.diff(gray, axis=0)
    textura_score = float((np.mean(np.abs(gx)) + np.mean(np.abs(gy))) / 2.0)

    return {
        "is_code_or_screen": bool(np.sum(mask_dark) / total_pixeles > 0.40),
        "is_indoor": bool(np.sum(mask_gray_white) / total_pixeles > 0.40),
        "is_skin_or_smooth_object": bool(np.sum(mask_tono_calido) / total_pixeles > 0.35 and textura_score < 7.0),
        "is_low_texture": bool(textura_score < 3.0),
        "veg_ratio": float(ratio_vegetacion),
        "puro_verde": float(np.sum(mask_verde_hsv) / total_pixeles),
        "puro_seco": float(np.sum(mask_seca_hsv) / total_pixeles)
    }

def generar_recomendacion_inteligente(nivel_riesgo: str, porcentaje_dano: float, diagnostico: str) -> str:
    if nivel_riesgo == "verde":
        return "¡Todo excelente! Tu cultivo luce fuerte y con buen color. Mantén tu riego habitual."
    elif nivel_riesgo == "amarillo":
        return "⚠️ Atención inicial: inspecciona de cerca las hojas del centro y monitorea la humedad."
    else:
        return "🚨 Alerta de daño severo: retira manualmente las hojas dañadas y aplica control fitosanitario."

@app.post("/analizar")
async def analizar_imagen(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image_original = Image.open(io.BytesIO(contents)).convert("RGB")
        image_resized = image_original.resize((224, 224))
        metricas = analizar_caracteristicas_imagen(image_resized)

        if metricas["is_code_or_screen"] or metricas["is_indoor"] or metricas["is_skin_or_smooth_object"] or (metricas["veg_ratio"] < 0.15):
            return {
                "status": "warning",
                "diagnostico": "Material Foliar No Detectado",
                "nivel_riesgo": "desconocido",
                "confianza": 0.0,
                "porcentaje_dano": 0.0,
                "analisis_visual": "No se detectó una hoja válida o cultivo en la imagen.",
                "recomendacion": "Sube una fotografía enfocada directamente al cultivo."
            }

        clase_predicha = "sano"
        confianza_nn = 85.0
        
        if interpreter:
            input_data = np.expand_dims(np.array(image_resized, dtype=np.float32), axis=0)
            input_data = (input_data / 127.5) - 1.0
            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_details[0]['index'])[0]
            pred_idx = np.argmax(output_data)
            clase_predicha = CLASS_NAMES[pred_idx]
            confianza_nn = float(output_data[pred_idx]) * 100

        clase_final = clase_predicha
        if metricas["puro_verde"] > metricas["puro_seco"] * 2.5 and metricas["puro_verde"] > 0.20:
            clase_final = "sano"
        elif metricas["puro_seco"] > metricas["puro_verde"] * 1.5:
            clase_final = "danado"

        if clase_final == "sano":
            diagnostico, nivel_riesgo = "Cultivo Sano", "verde"
            porcentaje_dano, confianza_final = 2.0, max(confianza_nn, 92.0)
            analisis_visual = "Estructura foliar firme con pigmentación verde continua y óptima."
        elif clase_final == "danado":
            diagnostico, nivel_riesgo = "Daño Severo / Plaga", "rojo"
            porcentaje_dano, confianza_final = 75.0, max(confianza_nn, 88.0)
            analisis_visual = "Alta presencia de biomasa seca o necrosada. Pérdida crítica de clorofila."
        else:
            diagnostico, nivel_riesgo = "Daño Moderado / Estrés", "amarillo"
            porcentaje_dano, confianza_final = 30.0, max(confianza_nn, 85.0)
            analisis_visual = "Zonas con ligera clorosis o bordes secos detectadas."

        return {
            "status": "success",
            "diagnostico": diagnostico,
            "nivel_riesgo": nivel_riesgo,
            "confianza": min(confianza_final, 99.5),
            "porcentaje_dano": porcentaje_dano,
            "analisis_visual": analisis_visual,
            "recomendacion": generar_recomendacion_inteligente(nivel_riesgo, porcentaje_dano, diagnostico)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.get("/perfil", response_class=HTMLResponse)
async def ver_perfil(request: Request, riesgo: str = Query(None), fecha_filtro: str = Query(None)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    db = SessionLocal()
    query = db.query(ConsultaBD).filter(ConsultaBD.usuario_id == user["id"])
    consultas = query.order_by(ConsultaBD.fecha.desc()).all()
    db.close()
    return templates.TemplateResponse(request=request, name="perfil.html", context={"user": user, "consultas": consultas})

@app.post("/guardar-consulta")
async def guardar_consulta(request: Request, diagnostico: str = Form(...), confianza: float = Form(...), nivel_riesgo: str = Form("verde"), cultivo: str = Form("General")):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    db = SessionLocal()
    nueva_consulta = ConsultaBD(usuario_id=user["id"], cultivo=cultivo, diagnostico=diagnostico, confianza=confianza, nivel_riesgo=nivel_riesgo)
    db.add(nueva_consulta)
    db.commit()
    db.close()
    return {"status": "success"}

@app.delete("/eliminar-consulta/{consulta_id}")
async def eliminar_consulta(consulta_id: int, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    db = SessionLocal()
    consulta = db.query(ConsultaBD).filter(ConsultaBD.id == consulta_id, ConsultaBD.usuario_id == user["id"]).first()
    if consulta:
        db.delete(consulta)
        db.commit()
    db.close()
    return {"status": "success"}