from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import materials, search, votes, auth, threads # <-- Добавили threads

app = FastAPI(title="Student Hub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(materials.router)
app.include_router(search.router)
app.include_router(votes.router)
app.include_router(auth.router)
app.include_router(threads.router) # <-- Подключили

@app.get("/health")
async def health():
    return {"ok": True}