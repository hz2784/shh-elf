from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from passlib.context import CryptContext
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shh_elf.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_email_verified = Column(String(10), default='false', nullable=False)
    email_verification_token = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_title = Column(String(255), nullable=False)
    recipient_name = Column(String(100), nullable=False)
    relationship = Column(String(50), nullable=False, default="朋友")
    recipient_interests = Column(Text, default="")
    tone = Column(String(50), nullable=False, default="友好热情")
    language = Column(String(20), nullable=False, default="中文")
    dialect = Column(String(50), default="zh-CN-XiaoxiaoNeural")
    recommendation_text = Column(Text, nullable=False)
    audio_path = Column(String(255), nullable=False)
    share_id = Column(String(32), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Add relationships after class definitions
User.recommendations = relationship("UserRecommendation", back_populates="user")
UserRecommendation.user = relationship("User", back_populates="recommendations")

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, password: str):
    hashed_password = User.get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_user_recommendation(
    db: Session,
    user_id: int,
    book_title: str,
    recipient_name: str,
    relationship: str,
    recipient_interests: str,
    tone: str,
    language: str,
    dialect: str,
    recommendation_text: str,
    audio_path: str,
    share_id: str
):
    db_recommendation = UserRecommendation(
        user_id=user_id,
        book_title=book_title,
        recipient_name=recipient_name,
        relationship=relationship,
        recipient_interests=recipient_interests,
        tone=tone,
        language=language,
        dialect=dialect,
        recommendation_text=recommendation_text,
        audio_path=audio_path,
        share_id=share_id
    )
    db.add(db_recommendation)
    db.commit()
    db.refresh(db_recommendation)
    return db_recommendation

def get_user_recommendations(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(UserRecommendation).filter(
        UserRecommendation.user_id == user_id
    ).order_by(UserRecommendation.created_at.desc()).offset(skip).limit(limit).all()

def get_recommendation_by_share_id(db: Session, share_id: str):
    return db.query(UserRecommendation).filter(
        UserRecommendation.share_id == share_id
    ).first()

def get_user_by_verification_token(db: Session, token: str):
    return db.query(User).filter(User.email_verification_token == token).first()

def verify_user_email(db: Session, user: User):
    user.is_email_verified = 'true'
    user.email_verification_token = None
    db.commit()
    db.refresh(user)
    return user

def update_verification_token(db: Session, user: User, token: str):
    user.email_verification_token = token
    db.commit()
    db.refresh(user)
    return user

# Gallery related functions
def get_book_by_isbn(db: Session, isbn: str):
    from book_gallery import BookTalkGallery
    return db.query(BookTalkGallery).filter(BookTalkGallery.isbn == isbn).first()

def update_book_audio_urls(db: Session, isbn: str, sample_url: str, talk_url: str):
    from book_gallery import BookTalkGallery
    book = db.query(BookTalkGallery).filter(BookTalkGallery.isbn == isbn).first()
    if book:
        book.sample_audio_cloudinary_url = sample_url
        book.book_talk_audio_cloudinary_url = talk_url
        db.commit()
        db.refresh(book)
    return book

def create_book_if_not_exists(db: Session, book_data: dict):
    from book_gallery import BookTalkGallery
    import json

    existing_book = get_book_by_isbn(db, book_data["isbn"])
    if existing_book:
        return existing_book

    new_book = BookTalkGallery(
        title=book_data["title"],
        author=book_data["author"],
        isbn=book_data["isbn"],
        cefr_level=book_data["cefr_level"],
        estimated_vocabulary=book_data["estimated_vocabulary"],
        formal_models=json.dumps(book_data["formal_models"]),
        sample_paragraph=book_data["sample_paragraph"],
        sample_audio_path=f"audio/gallery_sample_{book_data['isbn']}.mp3",
        book_talk_text=book_data["book_talk_text"],
        book_talk_audio_path=f"audio/gallery_talk_{book_data['isbn']}.mp3",
        genre=book_data["genre"],
        publication_year=book_data["publication_year"],
        page_count=book_data.get("page_count"),
        goodreads_rating=book_data.get("goodreads_rating")
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book