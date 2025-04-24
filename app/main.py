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
import uuid
import traceback

# Улучшенная настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Определение констант
UPLOAD_DIR = Path("uploads")
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"]

# Создание таблиц в базе данных (если их ещё нет)
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    
    # Создаем тестового пользователя
    db = SessionLocal()
    try:
        test_device_id = "test-device-001"
        test_user = crud.get_user_by_device_id(db, test_device_id)
        if not test_user:
            test_user = models.User(
                device_id=test_device_id,
                name="Михаил",
                age=18,
                car="Mercedes Benz S-class W220",
                region="Новосибирск",
                about="Каждый чёткий пацан должен купить себе старого немца"
            )
            db.add(test_user)
            db.commit()
            logger.info("Test user created successfully")
    except Exception as e:
        logger.error(f"Error creating test user: {str(e)}")
        db.rollback()
    finally:
        db.close()
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

app = FastAPI(
    title="Auto Enthusiasts Dating App",
    description="API для приложения знакомств автолюбителей",
    version="1.0.0",
    debug=True
)

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kileniass.github.io"],  # Разрешаем только наш домен
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Добавляем обработчик OPTIONS запросов
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "https://kileniass.github.io"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept, Origin"
    return response

# Dependency для получения DB сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()

# Улучшенный middleware для логирования запросов
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        logger.info(f"[{request_id}] Request: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"[{request_id}] Response: {response.status_code} (took {process_time:.2f} seconds)")
            return response
        except Exception as e:
            logger.error(f"[{request_id}] Error: {str(e)}\n{traceback.format_exc()}")
            raise

app.add_middleware(RequestLoggingMiddleware)

# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Auto Enthusiasts Dating App!"}

@app.post("/api/init", 
    summary="Инициализация пользователя",
    description="Создает нового пользователя с уникальным device_id или возвращает существующего",
    response_description="Данные пользователя")
async def init_user(db: Session = Depends(get_db)):
    try:
        # Генерируем уникальный device_id
        device_id = crud.generate_device_id()
        
        # Создаем нового пользователя
        user_create = UserCreate(device_id=device_id)
        user = crud.create_user(db, user_create)
        
        return {
            "user_id": user.id,
            "device_id": user.device_id,
            "name": user.name,
            "age": user.age,
            "car": user.car,
            "region": user.region,
            "about": user.about,
            "photo_url": user.photo_url
        }
    except Exception as e:
        logger.error(f"Error in init_user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{device_id}",
    summary="Обновление профиля пользователя",
    description="Обновляет данные профиля пользователя",
    response_description="Обновленные данные пользователя")
def update_user_profile(device_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    updated_user = crud.update_user(db, device_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.get("/api/users/{device_id}",
    summary="Получение профиля пользователя",
    description="Возвращает данные профиля пользователя",
    response_description="Данные пользователя")
def get_profile(device_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_device_id(db, device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users/{device_id}/like/{target_id}",
    summary="Лайк профиля",
    description="Отправляет лайк пользователю и проверяет на совпадение",
    response_description="Результат лайка и информация о совпадении")
def like_profile(device_id: str, target_id: int, db: Session = Depends(get_db)):
    user = crud.get_user_by_device_id(db, device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    like, match = crud.like_user(db, user.id, target_id)
    return {"match": match is not None}

@app.post("/api/users/{device_id}/dislike/{target_id}",
    summary="Дизлайк профиля",
    description="Отправляет дизлайк пользователю",
    response_description="Подтверждение дизлайка")
def dislike_profile(device_id: str, target_id: int, db: Session = Depends(get_db)):
    user = crud.get_user_by_device_id(db, device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    crud.dislike_user(db, user.id, target_id)
    return {"status": "success"}

@app.get("/api/users/{device_id}/next",
    summary="Получение следующего профиля",
    description="Возвращает следующий профиль для просмотра",
    response_description="Данные профиля")
def next_profile(device_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_device_id(db, device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    next_user = crud.get_next_profile(db, user.id)
    if not next_user:
        return {"profile": None}
    return {"profile": next_user}

@app.get("/api/users/{device_id}/matches",
    summary="Получение совпадений",
    description="Возвращает список пользователей, с которыми есть совпадение",
    response_description="Список совпадений")
def get_matches(device_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_device_id(db, device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    matches = crud.get_matches(db, user.id)
    return matches

@app.post("/api/users/{device_id}/photo",
    summary="Загрузка фото профиля",
    description="Загружает новое фото профиля",
    response_description="URL загруженного фото")
async def upload_photo(device_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_device_id(db, device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        # Создаем директорию для загрузок, если её нет
        UPLOAD_DIR.mkdir(exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_extension = file.filename.split('.')[-1]
        filename = f"{device_id}_{int(time.time())}.{file_extension}"
        file_path = UPLOAD_DIR / filename
        
        # Сохраняем файл
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Обновляем URL фото в профиле
        photo_url = f"/static/photos/{filename}"
        updated_user = crud.update_user_photo(db, device_id, photo_url)
        
        return {"photo_url": photo_url}
    except Exception as e:
        logger.error(f"Error uploading photo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading file")
