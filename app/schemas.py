from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    telegram_id: str

class UserCreate(UserBase):
    name: Optional[str] = None
    age: Optional[int] = None
    photo_url: Optional[str] = None
    car: Optional[str] = None
    region: Optional[str] = None
    about: Optional[str] = None

class UserUpdate(BaseModel):
    name: str
    age: int
    photo_url: Optional[str] = None
    car: str
    region: str
    about: Optional[str] = None

class User(UserBase):
    id: int
    name: str
    age: int
    photo_url: Optional[str] = None
    car: str
    region: str
    about: Optional[str] = None

    class Config:
        from_attributes = True

class LikeCreate(BaseModel):
    from_user_id: int
    to_user_id: int

class MatchRead(BaseModel):
    id: int
    user1_id: int
    user2_id: int

    class Config:
        from_attributes = True

class AboutUpdate(BaseModel):
    user_id: int
    about: str

class PhotoUpload(BaseModel):
    photo_url: str