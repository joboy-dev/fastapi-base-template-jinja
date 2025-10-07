from fastapi import APIRouter, Request
from api.core.dependencies.context import add_template_context
from api.utils.loggers import create_logger


external_router = APIRouter(tags=["External"])
logger = create_logger(__name__)

@external_router.get("/")
@add_template_context('pages/index.html')
async def index(request: Request) -> dict:
    return {}