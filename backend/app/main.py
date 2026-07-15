from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401 (ensure models are registered before create_all)
from app.routers import interactions, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM — HCP Module API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactions.router)
app.include_router(interactions.hcp_router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
