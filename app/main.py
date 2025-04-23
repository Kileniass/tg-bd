import os
import time
import shutil
import logging
from typing import Callable
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app import models, crud, database, utils
from app.database import SessionLocal, engine
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.schemas import AboutUpdate, UserUpdate, UserCreate, User as UserSchema, LikeCreate, MatchRead, PhotoUpload
import random
import string

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определение констант
CURRENT_SESSION_ID = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
UPLOAD_DIR = Path("uploads")
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"]

# Создание таблиц в базе данных (если их ещё нет)
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

app = FastAPI(
    title="Telegram WebApp for Auto Enthusiasts",
    description="API для приложения знакомств автолюбителей",
    version="1.0.0",
    debug=True
)

# Middleware для CORS - разрешаем запросы с любых доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых доменов
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы: GET, POST и т.д.
    allow_headers=["*"],  # Разрешаем все заголовки
)

# Dependency для получения DB сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Middleware для логирования запросов
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request details
        logger.info(f"Request: {request.method} {request.url}")
        if request.query_params:
            logger.debug(f"Query params: {dict(request.query_params)}")
        
        if request.method in ['POST', 'PUT']:
            try:
                if not request.headers.get('content-type', '').startswith('multipart/form-data'):
                    body = await request.body()
                    if body:
                        logger.debug(f"Request body: {body.decode()}")
            except Exception as e:
                logger.error(f"Error reading request body: {str(e)}")
        
        # Process request
        response = await call_next(request)
        
        # Log response details
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} (took {process_time:.2f} seconds)")
        
        return response

# Добавляем middleware для логирования
app.add_middleware(RequestLoggingMiddleware)

@app.get("/")
async def read_root(request: Request):
    logger.info(f"Root endpoint accessed from {request.client.host}")
    return {
        "message": "Welcome to the auto racing community!",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json"
    }

@app.options("/{rest_of_path:path}")
async def options_route(request: Request, rest_of_path: str):
    logger.debug(f"OPTIONS request received for /{rest_of_path}")
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "https://kileniass.github.io",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        }
    )

@app.get("/api/init/{telegram_id}", 
    summary="Инициализация пользователя",
    description="Создает нового пользователя или возвращает существующего",
    response_description="Данные пользователя")
async def init_user(telegram_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Starting user initialization for telegram_id: {telegram_id}")
        
        # Проверяем, существует ли пользователь с таким telegram_id
        logger.info("Querying database for existing user")
        user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
        
        if not user:
            logger.info("User not found, creating new user")
            # Создаем нового пользователя с минимальными данными
            user = models.User(
                telegram_id=telegram_id,
                session_id=CURRENT_SESSION_ID,
                is_new=True,
                name=None,
                age=None,
                car=None,
                region=None,
                about=None,
                photo_url=None
            )
            logger.info("Adding new user to database")
            db.add(user)
        else:
            logger.info(f"Existing user found: {user.id}")
            # Обновляем session_id для существующего пользователя
            user.session_id = CURRENT_SESSION_ID
            user.is_new = False
        
        logger.info("Committing changes to database")
        db.commit()
        logger.info("Refreshing user object")
        db.refresh(user)
        
        response = {
            "user_id": user.id,
            "session_id": user.session_id,
            "is_new": user.is_new,
            "name": user.name,
            "age": user.age,
            "car": user.car,
            "region": user.region,
            "about": user.about,
            "photo_url": user.photo_url
        }
        logger.info(f"Returning response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error in init_user: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.put("/api/users/{session_id}",
    summary="Обновление профиля пользователя",
    description="Обновляет данные профиля пользователя",
    response_description="Обновленные данные пользователя")
def update_user_profile(session_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    updated_user = crud.update_user(db, session_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.get("/api/users/{session_id}",
    summary="Получение профиля пользователя",
    description="Возвращает данные профиля пользователя",
    response_description="Данные пользователя")
async def get_profile(session_id: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"Fetching profile for user with session ID: {session_id}")
        user = crud.get_user_by_telegram_id(db, session_id)
        if not user:
            logger.error(f"User not found: {session_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except Exception as e:
        logger.error(f"Error fetching profile for user {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/profiles/{user_id}/like",
    summary="Лайк профиля",
    description="Отправляет лайк пользователю и проверяет на совпадение",
    response_description="Результат лайка и информация о совпадении")
def like_profile(user_id: int, current_user_id: int, db: Session = Depends(get_db)):
    like, match = crud.like_user(db, current_user_id, user_id)
    return {"like": like.id if like else None, "match": match.id if match else None}

@app.post("/api/profiles/{user_id}/dislike",
    summary="Дизлайк профиля",
    description="Отправляет дизлайк пользователю",
    response_description="Подтверждение дизлайка")
def dislike_profile(user_id: int, current_user_id: int, db: Session = Depends(get_db)):
    crud.dislike_user(db, current_user_id, user_id)
    return {"message": "Profile disliked"}

@app.get("/api/profiles/next",
    summary="Получение следующего профиля",
    description="Возвращает следующий профиль для просмотра",
    response_description="Данные профиля")
def next_profile(current_user_id: int, db: Session = Depends(get_db)):
    profile = crud.get_next_profile(db, current_user_id)
    if profile:
        return {
            "profile": {
                "id": profile.id,
                "name": profile.name,
                "age": profile.age,
                "photo_url": profile.photo_url,
                "car": profile.car,
                "region": profile.region,
                "about": profile.about
            }
        }
    else:
        return {"message": "No more profiles"}

@app.get("/api/matches/{user_id}",
    summary="Получение совпадений",
    description="Возвращает список пользователей, с которыми есть совпадение",
    response_description="Список совпадений")
def matches(user_id: int, db: Session = Depends(get_db)):
    matched_users = crud.get_matches(db, user_id)
    return {
        "matches": [
            {
                "id": user.id,
                "name": user.name,
                "age": user.age,
                "photo_url": user.photo_url,
                "car": user.car,
                "region": user.region,
                "about": user.about
            }
            for user in matched_users
        ]
    }

@app.get("/api/generate-password",
    summary="Генерация пароля",
    description="Генерирует случайный пароль",
    response_description="Сгенерированный пароль")
def generate_password():
    password = utils.generate_password()
    return {"password": password}

@app.put("/api/profiles/about",
    summary="Обновление описания",
    description="Обновляет раздел 'О себе' в профиле",
    response_description="Обновленное описание")
def update_about(data: AboutUpdate, db: Session = Depends(get_db)):
    user = crud.update_about(db, data.user_id, data.about)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/photos/upload/{session_id}")
async def upload_photo(session_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Validate file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )

        # Create upload directory if it doesn't exist
        UPLOAD_DIR.mkdir(exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = int(time.time())
        file_extension = file.filename.split('.')[-1]
        filename = f"{session_id}_{timestamp}.{file_extension}"
        file_path = UPLOAD_DIR / filename

        # Save file
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

        # Update user's photo URL in database
        user = db.query(models.User).filter(models.User.session_id == session_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.photo_url = f"/uploads/{filename}"
        db.commit()

        logger.info(f"Successfully uploaded photo for user {session_id}: {filename}")
        return {"photo_url": user.photo_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo for user {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during file upload")
    finally:
        file.file.close()
