from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    device_id: str = Field(..., description="Уникальный ID устройства")
    name: Optional[str] = Field(None, description="Имя пользователя")
    age: Optional[int] = Field(None, ge=18, le=100, description="Возраст пользователя")
    car: Optional[str] = Field(None, description="Автомобиль пользователя")
    region: Optional[str] = Field(None, description="Регион пользователя")
    about: Optional[str] = Field(None, description="О себе")

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 18 or v > 100):
            raise ValueError('Возраст должен быть от 18 до 100 лет')
        return v

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Имя пользователя")
    age: Optional[int] = Field(None, ge=18, le=100, description="Возраст пользователя")
    car: Optional[str] = Field(None, description="Автомобиль пользователя")
    region: Optional[str] = Field(None, description="Регион пользователя")
    about: Optional[str] = Field(None, description="О себе")
    photo_url: Optional[str] = Field(None, description="URL фотографии")

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 18 or v > 100):
            raise ValueError('Возраст должен быть от 18 до 100 лет')
        return v

class User(UserBase):
    id: int
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class LikeCreate(BaseModel):
    to_user_id: int = Field(..., description="ID пользователя, которому отправляется лайк")

class MatchRead(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class AboutUpdate(BaseModel):
    about: str = Field(..., min_length=10, max_length=500, description="Текст о себе")

class PhotoUpload(BaseModel):
    photo_url: str = Field(..., description="URL загруженной фотографии")