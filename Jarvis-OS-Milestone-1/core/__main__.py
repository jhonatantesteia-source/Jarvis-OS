import uvicorn
from core.config.settings import settings
if __name__ == "__main__":
    uvicorn.run("core.api.app:app", host=settings.host, port=settings.port, reload=settings.environment == "development")
