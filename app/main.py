from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app import models, crud, database, utils
from app.database import SessionLocal, engine
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import AboutUpdate 

# Создание таблиц в базе данных (если их ещё нет)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Telegram WebApp for Auto Enthusiasts")


#Укажи, с каких доменов можно обращаться к API
origins = [
    "https://web.telegram.org",           # для Telegram WebApp
    "https://tвой-фронт-домен.vercel.app",  # если фронт будет хоститься
    "http://localhost:3000"               # для разработки на React/Vue
]

#Middleware для CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # Разрешить все методы: GET, POST и т.д.
    allow_headers=["*"],   # Разрешить все заголовки
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

@app.post("/profiles/{user_id}/like")
def like_profile(user_id: int, current_user_id: int, db: Session = Depends(get_db)):
    like, match = crud.like_user(db, current_user_id, user_id)
    return {"like": like.id if like else None, "match": match.id if match else None}

@app.post("/profiles/{user_id}/dislike")
def dislike_profile(user_id: int, current_user_id: int, db: Session = Depends(get_db)):
    crud.dislike_user(db, current_user_id, user_id)
    return {"message": "Profile disliked"}

@app.get("/profiles/next")
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

@app.get("/matches/{user_id}")
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

@app.get("/generate-password")
def generate_password():
    password = utils.generate_password()
    return {"password": password}

@app.put("/profiles/about")
def update_about(data: AboutUpdate, db: Session = Depends(get_db)):
    user = crud.update_about(db, user_id=data.user_id, about_text=data.about)
    if user:
        return {"message": "About section updated", "about": user.about}
    else:
        return {"message": "User not found"}
