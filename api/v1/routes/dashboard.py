from datetime import timedelta
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request
from fastapi.responses import RedirectResponse
import psutil
from sqlalchemy.orm import Session
from decouple import config

from api.core.dependencies.context import add_template_context
from api.core.dependencies.flash_messages import MessageCategory, flash
from api.core.dependencies.form_builder import build_form
from api.db.database import get_db
from api.utils import paginator
from api.utils.settings import settings
from api.utils.loggers import create_logger
from api.v1.models.user import User
from api.v1.services.auth import AuthService
from api.v1.services.user import UserService


dashboard_router = APIRouter(prefix='/dashboard', tags=['Dashboard'])
logger = create_logger(__name__)

@dashboard_router.get('')
@add_template_context('pages/dashboard/index.html')
async def dashboard(request: Request, db: Session=Depends(get_db)):
    return {}
