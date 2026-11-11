"""Arranque aislado de laboratorio: uvicorn seguridad.app:app --port 8013."""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from .api import mount

app = FastAPI(title='BNA · Seguridad · Prototipo local', version='0.2.0')
mount(app)


@app.get('/', include_in_schema=False)
def console():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')
