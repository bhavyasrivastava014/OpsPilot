import sys
from pathlib import Path

from fastapi import FastAPI

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.settings import settings

from app.routes.health import router as health_router
from app.routes.root import router as root_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

    # CORS
    cors_origins = settings.get_cors_origins()
    if cors_origins:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )

    from app.routes.upload import router as upload_router
    from app.routes.extract import extract_router
    from app.routes.embed import router as embed_router
    from app.routes.retrieve import router as retrieve_router
    from app.routes.chat import router as chat_router
    from app.routes.documents import router as documents_router
    from app.routes.ingest import router as ingest_router

    app.include_router(root_router)
    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(extract_router)
    app.include_router(embed_router)
    app.include_router(retrieve_router)
    app.include_router(chat_router)
    app.include_router(documents_router)
    app.include_router(ingest_router)
    return app






app = create_app()





