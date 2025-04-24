from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from app import models, schemas
from typing import List, Tuple, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

def generate_device_id() -> str:
    """Генерирует уникальный ID устройства"""
    return str(uuid.uuid4())

def get_user_by_device_id(db: Session, device_id: str):
    """Получает пользователя по device_id"""
    try:
        return db.query(models.User).filter(models.User.device_id == device_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error getting user by device_id {device_id}: {str(e)}")
        raise

def create_user(db: Session, user: schemas.UserCreate):
    """Создает нового пользователя"""
    try:
        db_user = models.User(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except SQLAlchemyError as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise

def update_user(db: Session, device_id: str, user_update: schemas.UserUpdate):
    """Обновляет данные пользователя"""
    try:
        db_user = get_user_by_device_id(db, device_id)
        if not db_user:
            return None
            
        update_data = user_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
            
        db.commit()
        db.refresh(db_user)
        return db_user
    except SQLAlchemyError as e:
        logger.error(f"Error updating user {device_id}: {str(e)}")
        db.rollback()
        raise

def update_user_photo(db: Session, device_id: str, photo_url: str) -> Optional[models.User]:
    db_user = get_user_by_device_id(db, device_id)
    if db_user:
        db_user.photo_url = photo_url
        db.commit()
        db.refresh(db_user)
    return db_user

def like_user(db: Session, from_user_id: int, to_user_id: int):
    """Отправляет лайк пользователю"""
    try:
        # Проверяем, не было ли уже лайка
        existing_like = db.query(models.Like).filter(
            models.Like.from_user_id == from_user_id,
            models.Like.to_user_id == to_user_id
        ).first()
        
        if existing_like:
            return existing_like, None
            
        # Создаем новый лайк
        like = models.Like(from_user_id=from_user_id, to_user_id=to_user_id)
        db.add(like)
        
        # Проверяем на совпадение
        match = db.query(models.Like).filter(
            models.Like.from_user_id == to_user_id,
            models.Like.to_user_id == from_user_id
        ).first()
        
        if match:
            # Создаем запись о совпадении
            new_match = models.Match(user1_id=from_user_id, user2_id=to_user_id)
            db.add(new_match)
            
        db.commit()
        return like, match
    except SQLAlchemyError as e:
        logger.error(f"Error liking user {from_user_id} -> {to_user_id}: {str(e)}")
        db.rollback()
        raise

def dislike_user(db: Session, from_user_id: int, to_user_id: int):
    """Отправляет дизлайк пользователю"""
    try:
        # Проверяем, не было ли уже дизлайка
        existing_dislike = db.query(models.Dislike).filter(
            models.Dislike.from_user_id == from_user_id,
            models.Dislike.to_user_id == to_user_id
        ).first()
        
        if existing_dislike:
            return
            
        # Создаем новый дизлайк
        dislike = models.Dislike(from_user_id=from_user_id, to_user_id=to_user_id)
        db.add(dislike)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Error disliking user {from_user_id} -> {to_user_id}: {str(e)}")
        db.rollback()
        raise

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

def get_next_profile(db: Session, user_id: int):
    """Получает следующий профиль для просмотра"""
    try:
        # Получаем ID пользователей, которых уже лайкнули или дизлайкнули
        liked_users = db.query(models.Like.to_user_id).filter(models.Like.from_user_id == user_id)
        disliked_users = db.query(models.Dislike.to_user_id).filter(models.Dislike.from_user_id == user_id)
        
        # Ищем следующего пользователя, которого еще не видели
        next_user = db.query(models.User).filter(
            models.User.id != user_id,
            ~models.User.id.in_(liked_users),
            ~models.User.id.in_(disliked_users)
        ).first()
        
        return next_user
    except SQLAlchemyError as e:
        logger.error(f"Error getting next profile for user {user_id}: {str(e)}")
        raise

def get_matches(db: Session, user_id: int):
    """Получает список совпадений пользователя"""
    try:
        matches = db.query(models.Match).filter(
            (models.Match.user1_id == user_id) | (models.Match.user2_id == user_id)
        ).all()
        
        result = []
        for match in matches:
            other_user_id = match.user2_id if match.user1_id == user_id else match.user1_id
            other_user = db.query(models.User).filter(models.User.id == other_user_id).first()
            if other_user:
                result.append(other_user)
                
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error getting matches for user {user_id}: {str(e)}")
        raise

def update_about(db: Session, user_id: int, about_text: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.about = about_text
        db.commit()
        db.refresh(user)
    return user
