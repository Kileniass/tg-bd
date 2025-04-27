from pydantic import BaseModel

class UserBase(BaseModel):
    name: str = ""
    age: int = 0
    photo_url: str = ""
    car: str = ""
    region: str = ""
    about: str = ""

class UserCreate(UserBase):
    telegram_id: str

class UserUpdate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    telegram_id: str

    class Config:
        orm_mode = True

class LikeCreate(BaseModel):
    from_user_id: int
    to_user_id: int

class MatchRead(BaseModel):
    id: int
    user1_id: int
    user2_id: int

    class Config:
        orm_mode = True

class AboutUpdate(BaseModel):
    user_id: int
    about: str