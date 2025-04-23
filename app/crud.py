from sqlalchemy.orm import Session
from app import models, schemas

def get_user_by_telegram_id(db: Session, telegram_id: str):
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, telegram_id: str, user: schemas.UserUpdate):
    db_user = get_user_by_telegram_id(db, telegram_id)
    if db_user:
        for key, value in user.dict(exclude_unset=True).items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def like_user(db: Session, from_user_id: int, to_user_id: int):
    like = models.Like(from_user_id=from_user_id, to_user_id=to_user_id)
    db.add(like)
    db.commit()
    db.refresh(like)
    
    # После добавления лайка проверяем на матч
    match = create_match(db, from_user_id, to_user_id)
    return like, match

def dislike_user(db: Session, from_user_id: int, to_user_id: int):
    dislike = models.Dislike(from_user_id=from_user_id, to_user_id=to_user_id)
    db.add(dislike)
    db.commit()

def create_match(db: Session, from_user_id: int, to_user_id: int):
    # Если второй пользователь лайкнул первого, создаём матч
    reverse_like = db.query(models.Like).filter(
        models.Like.from_user_id == to_user_id,
        models.Like.to_user_id == from_user_id
    ).first()
    if reverse_like:
        match = models.Match(user1_id=from_user_id, user2_id=to_user_id)
        db.add(match)
        db.commit()
        db.refresh(match)
        return match
    return None

def get_all_skipped_ids(db: Session, user_id: int):
    liked = db.query(models.Like.to_user_id).filter(models.Like.from_user_id == user_id)
    disliked = db.query(models.Dislike.to_user_id).filter(models.Dislike.from_user_id == user_id)
    liked_ids = [id_tuple[0] for id_tuple in liked.all()]
    disliked_ids = [id_tuple[0] for id_tuple in disliked.all()]
    return liked_ids + disliked_ids

def get_next_profile(db: Session, current_user_id: int):
    skipped_ids = get_all_skipped_ids(db, current_user_id)
    return db.query(models.User).filter(
        models.User.id != current_user_id,
        ~models.User.id.in_(skipped_ids)
    ).first()

def get_matches(db: Session, user_id: int):
    return db.query(models.User).join(
        models.Match,
        (models.User.id == models.Match.user1_id) | (models.User.id == models.Match.user2_id)
    ).filter(
        (models.Match.user1_id == user_id) | (models.Match.user2_id == user_id)
    ).all()

def update_about(db: Session, user_id: int, about_text: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.about = about_text
        db.commit()
        db.refresh(user)
    return user
