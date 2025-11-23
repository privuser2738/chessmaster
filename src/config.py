"""
Configuration settings for ChessMaster Presentation System
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONTENT_DIR = DATA_DIR / "content"
IMAGES_DIR = DATA_DIR / "images"
PDFS_DIR = DATA_DIR / "pdfs"
PRESENTATIONS_DIR = DATA_DIR / "presentations"
CACHE_DIR = DATA_DIR / "cache"

# Ensure directories exist
for dir_path in [DATA_DIR, CONTENT_DIR, IMAGES_DIR, PDFS_DIR, PRESENTATIONS_DIR, CACHE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Speed settings (1-200 scale)
# 1 = extremely slow (~30 seconds per slide)
# 100 = default (~5 seconds per slide)
# 200 = very fast (~200ms per slide)
DEFAULT_SPEED = 100

def calculate_delay(speed: int) -> float:
    """
    Calculate delay in seconds based on speed setting (1-200).
    - Speed 1: ~30 seconds
    - Speed 100: ~5 seconds
    - Speed 150: ~2 seconds
    - Speed 200: ~0.2 seconds
    """
    speed = max(1, min(200, speed))  # Clamp to 1-200

    if speed <= 100:
        # Linear interpolation from 30s (speed=1) to 5s (speed=100)
        return 30 - (speed - 1) * (25 / 99)
    else:
        # Exponential decay from 5s (speed=100) to 0.2s (speed=200)
        # Using exponential for smooth fast transitions
        ratio = (speed - 100) / 100  # 0 to 1
        return 5 * (0.04 ** ratio)  # 5s to 0.2s

# Search topics for chess learning
CHESS_TOPICS = [
    # Beginner topics
    "chess basics for beginners",
    "how to play chess rules",
    "chess piece movements tutorial",
    "chess opening principles",
    "basic chess tactics",
    "chess checkmate patterns beginners",

    # Intermediate topics
    "chess opening theory",
    "chess middlegame strategy",
    "chess endgame techniques",
    "chess tactics puzzles",
    "positional chess concepts",
    "chess pawn structure",

    # Advanced topics
    "advanced chess strategy grandmaster",
    "chess calculation techniques",
    "chess prophylaxis strategy",
    "complex chess endgames",
    "chess sacrifices combinations",
    "famous chess games analysis",

    # Specific openings
    "sicilian defense chess",
    "ruy lopez opening",
    "queen's gambit chess",
    "italian game chess",
    "french defense chess",
    "caro-kann defense",

    # Famous players and games
    "magnus carlsen games analysis",
    "bobby fischer best games",
    "garry kasparov chess",
    "mikhail tal attacking chess",
    "anatoly karpov positional chess",

    # Chess concepts
    "chess piece activity",
    "king safety chess",
    "chess initiative tempo",
    "weak squares chess strategy",
    "chess outpost strategy",
    "chess exchange sacrifice"
]

# Trusted chess websites for content
CHESS_DOMAINS = [
    "chess.com",
    "lichess.org",
    "chesstempo.com",
    "chessbase.com",
    "chessgames.com",
    "thechesswebsite.com",
    "ichess.net",
    "chess24.com",
    "chessable.com"
]

# User agent for web requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Content settings
MAX_CONTENT_LENGTH = 50000  # Max characters per content piece
MIN_CONTENT_LENGTH = 100   # Minimum useful content length
MAX_IMAGES_PER_TOPIC = 10
MAX_PARAGRAPHS_PER_SLIDE = 3

# Presentation settings
PRESENTATION_TITLE = "ChessMaster Learning System"
BACKGROUND_COLOR = "#1a1a2e"
TEXT_COLOR = "#eaeaea"
ACCENT_COLOR = "#e94560"
SECONDARY_COLOR = "#16213e"
