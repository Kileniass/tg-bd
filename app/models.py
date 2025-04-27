from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    photo_url = Column(String, nullable=True)
    car = Column(String, nullable=False)
    region = Column(String, nullable=False)
    about = Column(String, nullable=True)

    # Связи с лайками и дизлайками
    likes = relationship("Like", back_populates="from_user", foreign_keys="[Like.from_user_id]")
    dislikes = relationship("Dislike", back_populates="from_user", foreign_keys="[Dislike.from_user_id]")

class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="likes")
    to_user = relationship("User", foreign_keys=[to_user_id])

class Dislike(Base):
    __tablename__ = "dislikes"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="dislikes")
    to_user = relationship("User", foreign_keys=[to_user_id])

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
