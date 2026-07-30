from fastapi import FastAPI, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 1. Montar archivos estáticos para las imágenes
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Configurar motor de plantillas
templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    # Sintaxis compatible con FastAPI/Starlette reciente:
    # "request" va como argumento con nombre, no dentro del diccionario.
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={}
    )


@app.post("/predict")
async def predict(request: Request, file: UploadFile = File(...)):
    # Simulación de respuesta de predicción
    prediction = "sano"
    confidence = 94.5
    recomendaciones = [
        "El cultivo presenta una excelente salud foliar.",
        "Mantener el esquema habitual de riego.",
        "Monitorear periódicamente para prevenir plagas."
    ]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "prediction": prediction,
            "confidence": confidence,
            "recomendaciones": recomendaciones
        }
    )