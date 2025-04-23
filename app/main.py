from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app import models, crud, database, utils, schemas
from app.database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import AboutUpdate
from fastapi.openapi.utils import get_openapi
import os
import shutil
from pathlib import Path

# Создание таблиц в базе данных (если их ещё нет)
models.Base.metadata.create_all(bind=engine)

# Создаем директорию для загруженных файлов
UPLOAD_DIR = Path("static/photos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Telegram WebApp for Auto Enthusiasts",
    description="API для приложения знакомств автолюбителей",
    version="1.0.0"
)

# Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kileniass.github.io"],  # Разрешаем запросы только с нашего домена
    allow_credentials=False,  # Отключаем credentials для CORS
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin"],
)

# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to the auto racing community!"}

@app.get("/api/init/{telegram_id}", 
    summary="Инициализация пользователя",
    description="Создает нового пользователя или возвращает существующего",
    response_description="Данные пользователя")
def init_user(telegram_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        new_user = schemas.UserCreate(telegram_id=telegram_id)
        user = crud.create_user(db, new_user)
    return user

@app.put("/api/users/{telegram_id}",
    summary="Обновление профиля пользователя",
    description="Обновляет данные профиля пользователя",
    response_description="Обновленные данные пользователя")
def update_user_profile(telegram_id: str, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    updated_user = crud.update_user(db, telegram_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.get("/api/users/{telegram_id}",
    summary="Получение профиля пользователя",
    description="Возвращает данные профиля пользователя",
    response_description="Данные пользователя")
def get_user_profile(telegram_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

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
    user = crud.update_about(db, user_id=data.user_id, about_text=data.about)
    if user:
        return {"message": "About section updated", "about": user.about}
    else:
        return {"message": "User not found"}

@app.post("/api/users/{telegram_id}/photo",
    summary="Загрузка фотографии профиля",
    description="Загружает фотографию профиля пользователя",
    response_description="URL загруженной фотографии")
async def upload_photo(
    telegram_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Проверяем существование пользователя
        user = crud.get_user_by_telegram_id(db, telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Проверяем тип файла
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Создаем уникальное имя файла
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"user_{telegram_id}{file_extension}"
        file_path = UPLOAD_DIR / filename

        # Сохраняем файл
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Обновляем URL фотографии в базе данных
        photo_url = f"/static/photos/{filename}"
        user.photo_url = photo_url
        db.commit()

        return {"photo_url": photo_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
