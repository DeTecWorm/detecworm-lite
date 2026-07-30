from fastapi import FastAPI, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={}
    )

@app.post("/predict")
async def predict(request: Request, file: UploadFile = File(...)):
    # Simulación de respuesta IA para la evaluación
    prediction = "Gusano Cogollero (Spodoptera frugiperda)"
    confidence = 96.8
    recomendaciones = [
        "Aplicar control biológico con Bacillus thuringiensis en fases tempranas.",
        "Monitorear las hojas centrales (cogollo) cada 3 días.",
        "Evitar el exceso de fertilizantes nitrogenados que atraigan la plaga."
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