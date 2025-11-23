"""
Data Manager Module
Handles storage, retrieval, and organization of chess content
Supports presentation queue system with continuous background generation
"""
import json
import os
import random
import threading
import queue
from pathlib import Path
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, asdict, field
from datetime import datetime
import hashlib

from config import (
    DATA_DIR, CONTENT_DIR, IMAGES_DIR, PDFS_DIR,
    PRESENTATIONS_DIR, CACHE_DIR
)


@dataclass
class Slide:
    """Represents a single presentation slide"""
    id: str
    title: str
    content: str
    excerpts: List[str]
    images: List[str]  # Local image paths
    source_url: str
    topic: str
    slide_type: str  # 'content', 'image', 'quote', 'title', 'summary', 'transition'
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Lesson:
    """Represents a complete lesson/presentation that plays once"""
    id: str
    title: str
    topic: str
    slides: List[Slide]
    created_at: str
    source_urls: List[str]
    estimated_duration: float  # seconds at speed 100
    status: str = "pending"  # pending, playing, completed


class PresentationQueue:
    """Thread-safe queue for managing lessons"""

    def __init__(self):
        self._queue: queue.Queue[Lesson] = queue.Queue()
        self._completed: List[Lesson] = []
        self._current: Optional[Lesson] = None
        self._lock = threading.Lock()
        self._lessons_played = 0

    def add_lesson(self, lesson: Lesson):
        """Add a lesson to the queue"""
        self._queue.put(lesson)
        print(f'[Queue] ADDED: {lesson.id[:8]} - size: {self._queue.qsize()}')

    def get_next_lesson(self, timeout: float = None) -> Optional[Lesson]:
        """Get the next lesson, marking current as completed"""
        with self._lock:
            if self._current:
                self._current.status = "completed"
                self._completed.append(self._current)
                self._lessons_played += 1
                self._current = None

        try:
            lesson = self._queue.get(timeout=timeout)
            with self._lock:
                lesson.status = "playing"
                self._current = lesson
            return lesson
        except queue.Empty:
            return None

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def current(self) -> Optional[Lesson]:
        return self._current

    @property
    def lessons_played(self) -> int:
        return self._lessons_played

    @property
    def completed_lessons(self) -> List[Lesson]:
        return self._completed.copy()

    def is_empty(self) -> bool:
        return self._queue.empty()


class DataManager:
    """Manages all data storage and retrieval for the presentation system"""

    def __init__(self):
        self.content_cache: Dict[str, dict] = {}
        self.used_content_ids: set = set()  # Track which content has been used
        self.presentation_queue = PresentationQueue()
        self._lock = threading.Lock()
        self._load_existing_content()

    def _load_existing_content(self):
        """Load previously fetched content from disk"""
        for content_file in CONTENT_DIR.glob("*.json"):
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    self.content_cache[content['id']] = content
            except Exception as e:
                print(f"Error loading {content_file}: {e}")

        print(f"Loaded {len(self.content_cache)} existing content items")

    def get_all_images(self) -> List[str]:
        """Get all available image paths"""
        images = []
        if IMAGES_DIR.exists():
            for topic_dir in IMAGES_DIR.iterdir():
                if topic_dir.is_dir():
                    for img_file in topic_dir.glob("*"):
                        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            images.append(str(img_file))
        return images

    def get_images_for_topic(self, topic: str) -> List[str]:
        """Get images for a specific topic"""
        topic_dir = IMAGES_DIR / topic.replace(' ', '_')[:30]
        if topic_dir.exists():
            return [str(f) for f in topic_dir.glob("*")
                    if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']]
        return []

    def get_unused_content(self) -> Optional[dict]:
        """Get content that hasn't been used in a presentation yet"""
        with self._lock:
            unused = [c for cid, c in self.content_cache.items()
                      if cid not in self.used_content_ids]
            if unused:
                content = random.choice(unused)
                self.used_content_ids.add(content['id'])
                return content
            # If all content used, reset and start over
            if self.content_cache:
                self.used_content_ids.clear()
                content = random.choice(list(self.content_cache.values()))
                self.used_content_ids.add(content['id'])
                return content
        return None

    def get_random_content(self) -> Optional[dict]:
        """Get a random content item"""
        if self.content_cache:
            return random.choice(list(self.content_cache.values()))
        return None

    def add_content(self, content_dict: dict):
        """Add new content to the cache"""
        content_id = content_dict.get('id')
        if content_id:
            with self._lock:
                self.content_cache[content_id] = content_dict
            # Save to disk
            content_file = CONTENT_DIR / f"{content_id}.json"
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(content_dict, f, indent=2, ensure_ascii=False)

    def create_slides_from_content(self, content_dict: dict) -> List[Slide]:
        """Create presentation slides from content"""
        slides = []
        content_id = content_dict.get('id', '')
        title = content_dict.get('title', 'Chess Learning')
        topic = content_dict.get('topic', 'chess')
        url = content_dict.get('url', '')
        excerpts = content_dict.get('excerpts', [])
        images = content_dict.get('local_images', [])

        # Title slide
        slides.append(Slide(
            id=f"{content_id}_title",
            title=title,
            content=f"Topic: {topic.title()}",
            excerpts=[],
            images=images[:1] if images else [],
            source_url=url,
            topic=topic,
            slide_type='title'
        ))

        # Content slides - one per excerpt
        for i, excerpt in enumerate(excerpts[:8]):
            slide_images = []
            if images and i < len(images):
                slide_images = [images[i]]
            elif images:
                slide_images = [random.choice(images)]

            slides.append(Slide(
                id=f"{content_id}_content_{i}",
                title=title,
                content=excerpt,
                excerpts=[],
                images=slide_images,
                source_url=url,
                topic=topic,
                slide_type='content'
            ))

        # Image showcase slides (if we have images)
        for i, img in enumerate(images[:2]):
            slides.append(Slide(
                id=f"{content_id}_image_{i}",
                title=f"{topic.title()} - Visual",
                content="",
                excerpts=[],
                images=[img],
                source_url=url,
                topic=topic,
                slide_type='image'
            ))

        return slides

    def build_lesson(self, content_items: List[dict], topic: str) -> Lesson:
        """Build a complete lesson from multiple content items"""
        lesson_id = hashlib.md5(
            f"{topic}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:10]

        all_slides = []
        source_urls = []

        # Intro slide
        all_slides.append(Slide(
            id=f"{lesson_id}_intro",
            title=f"Lesson: {topic.title()}",
            content=f"Welcome to this lesson on {topic}.\nLet's explore this topic together.",
            excerpts=[],
            images=[],
            source_url="",
            topic=topic,
            slide_type='title'
        ))

        # Build slides from each content item
        for idx, content in enumerate(content_items):
            slides = self.create_slides_from_content(content)
            all_slides.extend(slides)
            if content.get('url'):
                source_urls.append(content['url'])

            # Add transition between content items
            if idx < len(content_items) - 1:
                all_slides.append(Slide(
                    id=f"{lesson_id}_trans_{len(all_slides)}",
                    title="Continuing...",
                    content="Let's explore more about this topic.",
                    excerpts=[],
                    images=[],
                    source_url="",
                    topic=topic,
                    slide_type='transition'
                ))

        # Summary slide
        all_slides.append(Slide(
            id=f"{lesson_id}_summary",
            title=f"Lesson Complete: {topic.title()}",
            content=f"You've completed this lesson on {topic}.\n\nNext lesson loading...",
            excerpts=[],
            images=[],
            source_url="",
            topic=topic,
            slide_type='summary'
        ))

        # Estimate duration (5 seconds per slide at speed 100)
        estimated_duration = len(all_slides) * 5.0

        return Lesson(
            id=lesson_id,
            title=f"Chess Lesson: {topic.title()}",
            topic=topic,
            slides=all_slides,
            created_at=datetime.now().isoformat(),
            source_urls=source_urls,
            estimated_duration=estimated_duration
        )

    def queue_lesson(self, lesson: Lesson):
        """Add a lesson to the presentation queue"""
        self.presentation_queue.add_lesson(lesson)
        self._save_lesson(lesson)

    def get_next_lesson(self, timeout: float = None) -> Optional[Lesson]:
        """Get the next lesson to play"""
        return self.presentation_queue.get_next_lesson(timeout)

    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            'queue_size': self.presentation_queue.size,
            'lessons_played': self.presentation_queue.lessons_played,
            'current_lesson': self.presentation_queue.current.title if self.presentation_queue.current else None,
            'is_empty': self.presentation_queue.is_empty()
        }

    def _save_lesson(self, lesson: Lesson):
        """Save lesson to disk"""
        lesson_file = PRESENTATIONS_DIR / f"lesson_{lesson.id}.json"
        lesson_data = {
            'id': lesson.id,
            'title': lesson.title,
            'topic': lesson.topic,
            'created_at': lesson.created_at,
            'source_urls': lesson.source_urls,
            'slide_count': len(lesson.slides),
            'estimated_duration': lesson.estimated_duration,
            'slides': [asdict(s) for s in lesson.slides]
        }
        with open(lesson_file, 'w', encoding='utf-8') as f:
            json.dump(lesson_data, f, indent=2, ensure_ascii=False)

    def get_statistics(self) -> Dict:
        """Get statistics about stored data"""
        return {
            'total_content_items': len(self.content_cache),
            'total_images': len(self.get_all_images()),
            'unused_content': len(self.content_cache) - len(self.used_content_ids),
            'queue_size': self.presentation_queue.size,
            'lessons_played': self.presentation_queue.lessons_played,
            'topics': list(set(c.get('topic', '') for c in self.content_cache.values())),
            'lessons_saved': len(list(PRESENTATIONS_DIR.glob("lesson_*.json")))
        }


# Test
if __name__ == "__main__":
    dm = DataManager()
    stats = dm.get_statistics()
    print(f"Data Manager Stats: {stats}")
