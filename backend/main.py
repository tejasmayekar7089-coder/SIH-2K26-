"""
Entrypoint alias for uvicorn.
Allows running either `uvicorn app.main:app` or `uvicorn main:app`.
"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
