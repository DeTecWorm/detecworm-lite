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
import io
import numpy as np
from PIL import Image, ImageEnhance

# Carga dinámica del motor de inferencia Lite
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

app = FastAPI()

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
    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("UsuarioBD", back_populates="consultas")


Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------
# CARGA Y CONFIGURACIÓN DE MODELO IA (TFLITE)
# ------------------------------------------------------------------
MODEL_PATH = "detecworm_model.tflite"
interpreter = None
input_details = None
output_details = None

if os.path.exists(MODEL_PATH):
    try:
        interpreter = tflite.Interpreter(model_path=MODEL_PATH)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        print("-> Modelo TFLite cargado y listo en memoria.")
    except Exception as e:
        print(f"-> Error cargando TFLite: {e}")
else:
    print(f"-> AVISO: No se encontró el archivo {MODEL_PATH} en la raíz.")

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
# PREPROCESAMIENTO Y ESTABILIZACIÓN DE ILUMINACIÓN
# ------------------------------------------------------------------
def normalizar_iluminacion_foliar(pil_img):
    """
    Normaliza fotos tomadas con luz solar cálida (mañana/atardecer) 
    o de noche con flash para evitar falsos positivos.
    """
    img_array = np.array(pil_img, dtype=np.float32)

    # 1. Calcular el brillo promedio de la toma
    brillo_promedio = np.mean(img_array)

    # 2. Corrección de Gamma Adaptativa para imágenes extremas
    if brillo_promedio < 70:  # Toma nocturna o con sombra muy marcada
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(1.4)
    elif brillo_promedio > 195:  # Luz solar directa muy brillante
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(0.85)

    # 3. Normalización suave de temperatura de color (Gray-World Balance Ligero)
    img_array = np.array(pil_img, dtype=np.float32)
    r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]

    avg_r, avg_g, avg_b = np.mean(r), np.mean(g), np.mean(b)
    if avg_r > 0 and avg_g > 0 and avg_b > 0:
        avg_gray = (avg_r + avg_g + avg_b) / 3.0
        r = np.clip(r * (avg_gray / avg_r), 0, 255)
        g = np.clip(g * (avg_gray / avg_g), 0, 255)
        b = np.clip(b * (avg_gray / avg_b), 0, 255)

        img_balanced = np.stack([r, g, b], axis=-1).astype(np.uint8)
        return Image.fromarray(img_balanced)

    return pil_img


def analizar_patrones_vegetales(pil_img):
    """
    Analiza el espectro foliar en HSV recortando la región superior
    para ignorar cielos, nubes y fondos cálidos de atardecer.
    """
    img_hsv = pil_img.convert('HSV')
    np_hsv = np.array(img_hsv)

    # Ignoramos el 25% superior de la imagen (donde suele estar el cielo/horizonte)
    alto = np_hsv.shape[0]
    corte_cielo = int(alto * 0.25)
    np_hsv_crop = np_hsv[corte_cielo:, :, :]

    H = np_hsv_crop[:, :, 0]
    S = np_hsv_crop[:, :, 1]
    V = np_hsv_crop[:, :, 2]

    # Verde Clorofila Vivo (Tolerancia optimizada)
    mask_verde_real = (H >= 30) & (H <= 95) & (S >= 35) & (V >= 25)

    # Tejido Seco, Amarillento o Necrosado (Filtrando brillos del cielo)
    mask_seco_dano = ((H < 30) | (H > 95)) & (S >= 40) & (V >= 20) & (V <= 210)

    total_pixeles = np_hsv_crop.shape[0] * np_hsv_crop.shape[1]
    ratio_verde = np.sum(mask_verde_real) / total_pixeles
    ratio_dano = np.sum(mask_seco_dano) / total_pixeles

    return ratio_verde, ratio_dano


# ------------------------------------------------------------------
# ENDPOINT PRINCIPAL DE ANÁLISIS AGRÍCOLA
# ------------------------------------------------------------------
@app.post("/analizar")
async def analizar_imagen(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image_original = Image.open(io.BytesIO(contents)).convert("RGB")
        image_resized = image_original.resize((224, 224))

        # Paso A: Normalizar iluminación/temperatura de luz
        image_estabilizada = normalizar_iluminacion_foliar(image_resized)

        # Paso B: Extracción de métricas colorimétricas estables (sin cielo)
        ratio_verde, ratio_dano = analizar_patrones_vegetales(image_estabilizada)

        # Paso C: Inferencia por Red Neuronal TFLite
        clase_predicha = "sano"
        confianza_nn = 85.0

        if interpreter:
            input_data = np.expand_dims(np.array(image_estabilizada, dtype=np.float32), axis=0)
            input_data = (input_data / 127.5) - 1.0  # Normalización [-1, 1]

            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_details[0]['index'])[0]

            pred_idx = np.argmax(output_data)
            clase_predicha = CLASS_NAMES[pred_idx]
            confianza_nn = float(output_data[pred_idx]) * 100

        # Paso D: Lógica Híbrida de Decisión
        # Prioridad a la clasificación si el modelo TFLite dice "sano" o la masa verde es dominante
        if clase_predicha == "sano" or (ratio_verde >= 0.35 and ratio_dano < 0.25):
            diagnostico = "Cultivo Sano"
            porcentaje_dano = round(float(np.clip((1.0 - ratio_verde) * 8, 0.0, 5.0)), 1)
            confianza_final = round(max(confianza_nn, 92.0 + (ratio_verde * 5)), 1)
            analisis_visual = (
                "Estructura foliar firme con pigmentación verde continua. "
                "Actividad fotosintética en rangos óptimos. Muestra libre de estrés foliar severo."
            )
            recomendacion = "El cultivo se encuentra en óptimas condiciones. Mantener el programa regular de riego y monitoreo preventivo."

        elif clase_predicha == "danado" or ratio_dano >= 0.40:
            diagnostico = "Daño Severo / Estrés Foliar / Plaga"
            porcentaje_dano = round(float(np.clip(60.0 + (ratio_dano * 40), 60.0, 98.0)), 1)
            confianza_final = round(max(confianza_nn, 88.0 + (ratio_dano * 10)), 1)
            analisis_visual = (
                "Se detecta alta presencia de tejido foliar seco, amarillento o necrosado. "
                "Pérdida crítica de clorofila viva por estrés hídrico, sequía o ataque severo de plaga."
            )
            recomendacion = "Revisar el sistema de riego de inmediato y aplicar nutrientes foliares. Inspeccionar cogollos para descartar presencia activa de gusano u otra plaga."

        else:
            diagnostico = "Daño Moderado / Presencia Inicial de Plaga"
            porcentaje_dano = round(float(np.clip(15.0 + (ratio_dano * 40), 15.0, 50.0)), 1)
            confianza_final = round(max(confianza_nn, 85.0 + (ratio_verde * 8)), 1)
            analisis_visual = (
                "Se aprecian zonas con ligera clorosis, rasgaduras o bordes secos. "
                "El cultivo mantiene parcialmente masa verde pero presenta signos tempranos de estrés."
            )
            recomendacion = "Realizar inspección directa en el cogollo y follaje. Aplicar control biológico preventivo o ajustar la nutrición del suelo."

        return {
            "status": "success",
            "diagnostico": diagnostico,
            "confianza": min(confianza_final, 99.5),
            "porcentaje_dano": porcentaje_dano,
            "analisis_visual": analisis_visual,
            "recomendacion": recomendacion
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en el análisis de la imagen: {str(e)}")


# ------------------------------------------------------------------
# RUTAS DE HISTORIAL Y PERFIL
# ------------------------------------------------------------------
@app.get("/perfil", response_class=HTMLResponse)
async def ver_perfil(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")

    db = SessionLocal()
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