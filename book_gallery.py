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
        "sample_paragraph": "Mr. Jones, of the Manor Farm, had locked the hen-houses for the night, but was too drunk to remember to shut the popholes. With the ring of light from his lantern dancing from side to side, he lurched across the yard, kicked off his boots at the back door, drew himself a last glass of beer from the barrel in the scullery, and made his way up to bed, where Mrs. Jones was already snoring. As soon as the light in the bedroom went out there was a stirring and a fluttering all through the farm buildings. Word had gone round during the day that old Major, the prize Middle White boar, had had a strange dream on the previous night and wished to communicate it to the other animals. It had been agreed that they should all meet in the big barn as soon as Mr. Jones was safely out of the way. Old Major (so he was always called, though the name under which he had been exhibited was Willingdon Beauty) was twelve years old and had lately grown rather stout, but he was still a majestic-looking pig, with a wise and benevolent appearance in spite of the fact that his tushes had never been cut.",
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
        "sample_paragraph": "In my younger and more vulnerable years my father gave me some advice that I've carried with me ever since. 'Whenever you feel like criticizing anyone,' he told me, 'just remember that all the people in this world haven't had the advantages that you've had.' He didn't say any more, but we've always been unusually communicative in a reserved way, and I understood that he meant a great deal more than that. In consequence, I'm inclined to reserve all judgments, a habit that has opened up many curious natures to me and also made me the victim of not a few veteran bores. The abnormal mind is quick to detect and attach itself to this quality when it appears in a normal person, and so it came about that in college I was unjustly accused of being a politician, because I was privy to the secret griefs of wild, unknown men. Most of the big shore dinners were in East Egg, the fashionable East Egg where Daisy lived. Sometimes she and Miss Baker talked at once, unobtrusively and with a bantering inconsequence that was never quite chatter, that was as cool as their white dresses and their impersonal eyes in the absence of all desire.",
        "book_talk_text": "The Great Gatsby isn't just about the 1920s - it's about the eternal human desire to reinvent ourselves. Fitzgerald's lyrical prose will teach you about the beauty and tragedy of the American Dream...",
        "genre": "Literary Fiction",
        "publication_year": 1925,
        "page_count": 180,
        "goodreads_rating": 3.9
    },
    {
        "title": "My Year of Rest and Relaxation",
        "author": "Ottessa Moshfegh",
        "isbn": "9780525522133",
        "cefr_level": "B2",
        "estimated_vocabulary": 6500,
        "formal_models": ["nihilism", "social critique", "psychological realism"],
        "sample_paragraph": "Whenever I woke up, night or day, I'd shuffle through the bright marble lobby of my building on the Upper East Side, past the boring fake flower arrangement on the coffee table, past the doorman, and onto the street, and roam around, my eyes half closed, always drifting toward the closest place I could sit down. In Rite Aid, I'd sit in the back where the chairs were lined up for customers waiting for prescriptions. The pharmacist probably thought I was waiting to buy OxyContin or Adderall or whatever he thought a young woman like me would want. But I was just sitting there, just resting. I'd sit until the pharmacist asked if he could help me, then I'd buy a tube of lip balm or some mints and leave. I was very tired. Or I'd take the Stairmaster until I couldn't anymore, sometimes forty minutes, sometimes an hour and a half. I'd read magazines and go home. I was trying to get tired enough to sleep. This was in the beginning, when I first started taking the pills. I was supposed to take them only when I felt anxious, but I felt anxious all the time, so I was always taking them.",
        "book_talk_text": "What if you could sleep for a year and wake up to a completely new life? Ottessa Moshfegh's darkly funny novel follows a young woman who decides to hibernate through her problems. This brilliant exploration of modern malaise and privilege will challenge your assumptions about happiness, ambition, and what it means to be truly awake...",
        "genre": "Contemporary Fiction",
        "publication_year": 2018,
        "page_count": 304,
        "goodreads_rating": 3.7
    }
]