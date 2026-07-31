from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests

app = FastAPI()

# Clave de sesión encriptada
app.add_middleware(SessionMiddleware, secret_key="detecworm_super_secret_key_2026")

templates = Jinja2Templates(directory="templates")

GOOGLE_CLIENT_ID = "857174676804-8qj3u5ph6ut9drjar4rq2dis0mf6ctiq.apps.googleusercontent.com"

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
        # Tolerancia de 60 segundos por si el reloj del sistema tiene desfase
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
        
        request.session["user"] = user_data
        return {"status": "success", "user": user_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token inválido: {str(e)}")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")