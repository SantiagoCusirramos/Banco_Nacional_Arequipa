from fastapi import FastAPI

app = FastAPI(
    title="BNA - Backend",
    description="Backend del Banco Nacional de Arequipa",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "proyecto": "BNA",
        "status": "ok",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
