# Book Talk Gallery - MVP Implementation
# For English-learning Chinese speakers

from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from database import Base

class BookTalkGallery(Base):
    __tablename__ = "book_talk_gallery"

    id = Column(Integer, primary_key=True, index=True)

    # Basic book info
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    isbn = Column(String(20), unique=True, index=True)
    cover_url = Column(String(500))
    description = Column(Text)

    # For English learners
    cefr_level = Column(String(10))  # A2, B1, B2, C1, C2
    estimated_vocabulary = Column(Integer)  # 3000, 5000, 8000, etc.

    # Joshua Landy's Formal Models
    formal_models = Column(Text)  # JSON array: ["rational thinking", "form-giving"]

    # Sample content for preview
    sample_paragraph = Column(Text, nullable=False)  # 50-100 words excerpt
    sample_audio_path = Column(String(255), nullable=False)  # 1-minute read-aloud
    sample_duration_seconds = Column(Integer)  # ~60 seconds

    # Complete Book Talk
    book_talk_text = Column(Text, nullable=False)  # Full recommendation
    book_talk_audio_path = Column(String(255), nullable=False)  # Full book talk audio
    book_talk_duration_seconds = Column(Integer)  # ~2-3 minutes

    # Metadata
    genre = Column(String(100))
    publication_year = Column(Integer)
    page_count = Column(Integer)
    goodreads_rating = Column(Float)
    featured = Column(String(10), default='false')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Sample data structure for MVP
SAMPLE_BOOKS = [
    {
        "title": "Animal Farm",
        "author": "George Orwell",
        "isbn": "9780451526342",
        "cefr_level": "B1",
        "estimated_vocabulary": 4000,
        "formal_models": ["rational thinking", "allegory", "political awareness"],
        "sample_paragraph": "All animals are equal, but some animals are more equal than others. The creatures outside looked from pig to man, and from man to pig, and from pig to man again; but already it was impossible to say which was which.",
        "book_talk_text": "If you've ever wondered how power corrupts, Animal Farm is your perfect introduction to political literature. Orwell's masterpiece uses simple farm animals to reveal complex truths about human nature and society...",
        "genre": "Political Satire",
        "publication_year": 1945,
        "page_count": 112,
        "goodreads_rating": 3.9
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "isbn": "9780743273565",
        "cefr_level": "B2",
        "estimated_vocabulary": 6000,
        "formal_models": ["illusion vs reality", "form-giving", "American Dream critique"],
        "sample_paragraph": "So we beat on, boats against the current, borne back ceaselessly into the past. And as I sat there brooding on the old, unknown world, I thought of Gatsby's wonder when he first picked out the green light at the end of Daisy's dock.",
        "book_talk_text": "The Great Gatsby isn't just about the 1920s - it's about the eternal human desire to reinvent ourselves. Fitzgerald's lyrical prose will teach you about the beauty and tragedy of the American Dream...",
        "genre": "Literary Fiction",
        "publication_year": 1925,
        "page_count": 180,
        "goodreads_rating": 3.9
    }
]