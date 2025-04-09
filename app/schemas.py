from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    age: int
    photo_url: str
    car: str
    region: str

class UserRead(UserCreate):
    id: int

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
