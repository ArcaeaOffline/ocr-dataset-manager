import mimetypes
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi_problem_details import init_app as init_problem_details

from .config import settings
from .db import init_db
from .routers import catalog, images, imports

# Windows seeds mimetypes from the registry, where .js can map to
# text/plain; browsers refuse ES module scripts with a non-JS MIME.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


# operation ids become generated client function names
def _operation_id(route: APIRoute) -> str:
    head, *rest = route.name.split("_")
    return head + "".join(part.capitalize() for part in rest)


app = FastAPI(
    title="OCR Dataset Manager",
    lifespan=lifespan,
    generate_unique_id_function=_operation_id,
)

# errors become RFC 9457 problem+json; the library also injects the
# schema-wide `default` response, which is why the spec has no
# HTTPValidationError documentation
init_problem_details(app)

app.include_router(imports.router)
app.include_router(images.router)
app.include_router(catalog.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def register_spa(app: FastAPI, dist: Path) -> None:
    """Serve the built frontend from `dist`; non-API paths that match no
    file fall back to index.html (vue-router history mode). Call only
    after every API route is registered: the catch-all swallows
    whatever is registered later."""
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(index)


if settings.web_dist_dir is not None:
    register_spa(app, settings.web_dist_dir)
