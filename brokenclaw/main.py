import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Mount

from brokenclaw.auth import SUPPORTED_INTEGRATIONS, router as auth_router
from brokenclaw.config import get_settings
from brokenclaw.exceptions import AuthenticationError, IntegrationError, RateLimitError
from brokenclaw.mcp_server import mcp
from brokenclaw.routers.docs import router as docs_router
from brokenclaw.routers.drive import router as drive_router
from brokenclaw.routers.gmail import router as gmail_router
from brokenclaw.routers.sheets import router as sheets_router
from brokenclaw.routers.slides import router as slides_router
from brokenclaw.routers.tasks import router as tasks_router
from brokenclaw.routers.forms import router as forms_router
from brokenclaw.routers.maps import router as maps_router
from brokenclaw.routers.youtube import router as youtube_router
from brokenclaw.routers.calendar import router as calendar_router
from brokenclaw.routers.news import router as news_router


# --- Localhost-only middleware ---

class LocalhostOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else None
        if client_host not in ("127.0.0.1", "::1", "localhost"):
            return JSONResponse(
                status_code=403,
                content={"error_code": "forbidden", "message": "Localhost access only"},
            )
        return await call_next(request)


# --- FastAPI app ---

api = FastAPI(title="Brokenclaw", version="0.1.0")
api.include_router(auth_router)
api.include_router(gmail_router)
api.include_router(drive_router)
api.include_router(sheets_router)
api.include_router(docs_router)
api.include_router(slides_router)
api.include_router(tasks_router)
api.include_router(forms_router)
api.include_router(maps_router)
api.include_router(youtube_router)
api.include_router(calendar_router)
api.include_router(news_router)


@api.get("/api/status")
def api_status() -> dict:
    from brokenclaw.auth import _get_token_store

    store = _get_token_store()
    statuses = {}
    for name in SUPPORTED_INTEGRATIONS:
        accounts = store.list_accounts(name)
        statuses[name] = {
            "authenticated_accounts": accounts,
            "ready": len(accounts) > 0,
        }
    return {"integrations": statuses}


# --- Exception handlers ---

@api.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(status_code=401, content={"error_code": "auth_error", "message": str(exc)})


@api.exception_handler(IntegrationError)
async def integration_error_handler(request: Request, exc: IntegrationError):
    return JSONResponse(status_code=500, content={"error_code": "integration_error", "message": str(exc)})


@api.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    return JSONResponse(status_code=429, content={"error_code": "rate_limit", "message": str(exc)})


# --- Starlette root app ---

mcp_app = mcp.http_app(path="/", stateless_http=True)

app = Starlette(
    middleware=[Middleware(LocalhostOnlyMiddleware)],
    routes=[
        Mount("/mcp", app=mcp_app),
        Mount("/", app=api),
    ],
)


def run():
    settings = get_settings()
    uvicorn.run(
        "brokenclaw.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
