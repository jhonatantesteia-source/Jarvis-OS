from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config.settings import settings
from core.database.connection import initialize_database
from core.logging.logger import configure_logging
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level); initialize_database(); yield
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173","http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.get("/health")
def health(): return {"status":"online","service":"python-core","environment":settings.environment}
@app.get("/status")
def status(): return {"app":settings.app_name,"version":"0.1.0","environment":settings.environment,"core":"online","database":"initialized"}
