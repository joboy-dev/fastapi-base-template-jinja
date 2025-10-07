from datetime import timedelta
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from decouple import config

from api.core.dependencies.context import add_template_context
from api.core.dependencies.flash_messages import MessageCategory, flash
from api.core.dependencies.form_builder import build_form
from api.db.database import get_db
from api.utils.settings import settings
from api.utils.loggers import create_logger
from api.utils.responses import success_response
from api.utils.telex_notification import TelexNotification
from api.v1.models.user import User
from api.v1.services.auth import AuthService
from api.v1.services.user import UserService


auth_router = APIRouter(prefix='/auth', tags=['Auth'])
logger = create_logger(__name__)

@auth_router.api_route('/register', methods=["GET", "POST"])
@add_template_context('pages/auth/register.html')
async def register(
    request: Request,
    bg_tasks: BackgroundTasks,
    db: Session=Depends(get_db)
):
    """Endpoint to create a new user

    Args:
        payload (CreateUser): Payload containing first_name, last_name, email and password
        db (Session, optional): Database session. Defaults to Depends(get_db).
    """
    
    query = db.query(User).filter(User.is_admin == True)
    count = query.count()
    if count > 0:
        flash(request, 'Request access to the monitoring dashboard or login to your account', MessageCategory.INFO)
        return RedirectResponse(url="/auth/request-access", status_code=303)
    
    form = build_form(
        title='Register Account',
        subtitle='Create an account to get started',
        fields=[
            {
                'type': 'email',
                'label': 'Email',
                'name': 'email',
                'placeholder': 'e.g. john.doe@example.com',
                'required': True
            },
            {
                'type': 'password',
                'label': 'Password',
                'name': 'password',
                'placeholder': 'e.g. Password123',
                'required': True
            },
            {
                'type': 'password',
                'label': 'Confirm Password',
                'name': 'confirm_password',
                'placeholder': 'e.g. Password123',
                'required': True
            }
        ],
        button_text='Register',
        action='/auth/register'
    )
    
    context = {
        'form': form
    }
    
    if request.method == 'POST':
        payload = await request.form()
        
        try:
            new_user, access_token, refresh_token = UserService.create(
                db=db,
                payload=payload,
                bg_tasks=bg_tasks,
                is_active=True,
                is_admin=True,
                is_approved=True,
                create_token=True
            )
            
            logger.info(f'User {new_user.email} created successfully')
            
            flash(request, 'Signed up successfully', MessageCategory.SUCCESS)
            
            # Redirect to dashboard
            response = RedirectResponse(url="/dashboard", status_code=303)
            
            # Add refresh token to cookies
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                expires=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
                httponly=True,
                secure=True,
                samesite="none",
            )
            
            response.set_cookie(
                key="access_token",
                value=access_token,
                expires=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                httponly=True,
                secure=True,
                samesite="none",
            )
            
            return response
            
        except HTTPException as e:
            # Preserve form data on error
            flash(request, e.detail, MessageCategory.ERROR)
            context['form_data'] = dict(payload)
            return context
    
    return context


@auth_router.api_route('/request-access', methods=["GET", "POST"])
@add_template_context('pages/auth/request-access.html')
async def request_access(
    request: Request, 
    bg_tasks: BackgroundTasks,
    db: Session=Depends(get_db)
):
    """Endpoint to log in a user

    Args:
        payload (auth_schemas.LoginSchema): Contains email and password
        db (Session, optional): _description_. Defaults to Depends(get_db).
    """
    
    query = db.query(User)
    count = query.count()
    if count == 0:
        flash(request, 'No account found. Please register to continue', MessageCategory.INFO)
        return RedirectResponse(url="/auth/register", status_code=303)
    
    form = build_form(
        title='Request Administrator Access',
        subtitle='Request access to the monitoring dashboard',
        fields=[
            {
                'type': 'email',
                'label': 'Email',
                'name': 'email',
                'placeholder': 'e.g. john.doe@example.com',
                'required': True,
            },
            {
                'type': 'password',
                'label': 'Password',
                'name': 'password',
                'placeholder': 'e.g. Password123',
                'required': True
            },
            {
                'type': 'password',
                'label': 'Confirm Password',
                'name': 'confirm_password',
                'placeholder': 'e.g. Password123',
                'required': True
            }
        ],
        button_text='Request Access',
        action='/auth/request-access'
    )
    
    context = {
        'form': form
    }
    
    if request.method == 'POST':
        payload = await request.form()
        
        try:
            user, _, _ = UserService.create(
                db=db,
                payload=payload,
                bg_tasks=bg_tasks,
                is_active=False,
                is_admin=False,
                is_approved=False,
                create_token=False
            )
            
            logger.info(f'User {user.email} request made')
            
            flash(request, 'Access request made successfully', MessageCategory.SUCCESS)
            
            response = RedirectResponse(url="/auth/request-access", status_code=303)
            
            return response
            
        except HTTPException as e:
            # Preserve form data on error
            flash(request, e.detail, MessageCategory.ERROR)
            context['form_data'] = dict(payload)
            return context
    
    return context


@auth_router.api_route('/login', methods=["GET", "POST"])
@add_template_context('pages/auth/login.html')
async def login(
    request: Request, 
    db: Session=Depends(get_db)
):
    """Endpoint to log in a user

    Args:
        payload (auth_schemas.LoginSchema): Contains email and password
        db (Session, optional): _description_. Defaults to Depends(get_db).
    """
    
    query = db.query(User).filter(User.is_admin == True)
    count = query.count()
    logger.info(f'Existing admin user count: {count}')
    if count == 0:
        flash(request, 'No account found. Please register to continue', MessageCategory.INFO)
        return RedirectResponse(url="/auth/register", status_code=303)
    
    form = build_form(
        title='Administrator Access',
        subtitle='Secure login to monitoring dashboard',
        fields=[
            {
                'type': 'email',
                'label': 'Email',
                'name': 'email',
                'placeholder': 'e.g. john.doe@example.com',
                'required': True,
            },
            {
                'type': 'password',
                'label': 'Password',
                'name': 'password',
                'placeholder': 'e.g. Password123',
                'required': True
            }
        ],
        button_text='Login',
        action='/auth/login'
    )
    
    context = {
        'form': form
    }
    
    if request.method == 'POST':
        payload = await request.form()
                
        try:
            user, access_token, refresh_token = AuthService.authenticate(
                db, 
                email=payload.get('email'), 
                password=payload.get('password')
            )
            
            logger.info(f'User {user.email} logged in successfully')
            
            flash(request, 'Logged in successfully', MessageCategory.SUCCESS)
            
            response = RedirectResponse(url="/dashboard", status_code=303)
            
            # Add refresh token to cookies
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                expires=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
                httponly=True,
                secure=True,
                samesite="none",
            )
            
            response.set_cookie(
                key="access_token",
                value=access_token,
                expires=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                httponly=True,
                secure=True,
                samesite="none",
            )
            
            return response
            
        except HTTPException as e:
            # Preserve form data on error
            flash(request, e.detail, MessageCategory.ERROR)
            context['form_data'] = dict(payload)
            return context
    
    return context


@auth_router.post('/logout')
async def logout(request: Request, db: Session=Depends(get_db)):
    """Endpoint to log a user out

    Args:
        db (Session, optional): _description_. Defaults to Depends(get_db).
    """
    
    current_user = request.state.current_user
    
    AuthService.logout(db, current_user.id)
    request.state.current_user = None
    
    response = RedirectResponse(url="/auth/login", status_code=303)
    
    # Add refresh token to cookies
    response.delete_cookie('refresh_token')
    response.delete_cookie('access_token')
    
    return response
