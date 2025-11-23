"""
Data Manager Module
Handles storage, retrieval, and organization of chess content
"""
import json
import os
import random
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
    slide_type: str  # 'content', 'image', 'quote', 'title', 'summary'
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Presentation:
    """Represents a presentation session"""
    id: str
    name: str
    slides: List[Slide]
    created_at: str
    topics_covered: List[str]


class DataManager:
    """Manages all data storage and retrieval for the presentation system"""

    def __init__(self):
        self.content_cache: Dict[str, dict] = {}
        self.slide_queue: List[Slide] = []
        self.current_presentation: Optional[Presentation] = None
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

    def get_random_content(self) -> Optional[dict]:
        """Get a random content item"""
        if self.content_cache:
            return random.choice(list(self.content_cache.values()))
        return None

    def get_content_by_topic(self, topic: str) -> List[dict]:
        """Get all content items for a topic"""
        return [c for c in self.content_cache.values()
                if topic.lower() in c.get('topic', '').lower()]

    def add_content(self, content_dict: dict):
        """Add new content to the cache"""
        content_id = content_dict.get('id')
        if content_id:
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

        # Image showcase slides
        for i, img in enumerate(images[:3]):
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

    def generate_slides(self, max_slides: int = 50) -> Generator[Slide, None, None]:
        """Generate slides from available content (infinite generator)"""
        while True:
            # Shuffle content for variety
            content_items = list(self.content_cache.values())
            random.shuffle(content_items)

            for content in content_items:
                slides = self.create_slides_from_content(content)
                for slide in slides:
                    yield slide

            # If no content yet, yield placeholder
            if not content_items:
                yield Slide(
                    id="loading",
                    title="Loading Chess Content...",
                    content="Searching the web for chess tutorials and lessons...",
                    excerpts=[],
                    images=[],
                    source_url="",
                    topic="loading",
                    slide_type='title'
                )

    def queue_slides(self, slides: List[Slide]):
        """Add slides to the presentation queue"""
        self.slide_queue.extend(slides)

    def get_next_slide(self) -> Optional[Slide]:
        """Get the next slide from the queue"""
        if self.slide_queue:
            return self.slide_queue.pop(0)
        return None

    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.slide_queue)

    def start_presentation(self, name: str = None) -> Presentation:
        """Start a new presentation session"""
        pres_id = hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:8]
        name = name or f"Chess Learning Session {pres_id}"

        self.current_presentation = Presentation(
            id=pres_id,
            name=name,
            slides=[],
            created_at=datetime.now().isoformat(),
            topics_covered=[]
        )

        return self.current_presentation

    def add_slide_to_presentation(self, slide: Slide):
        """Add a slide to the current presentation"""
        if self.current_presentation:
            self.current_presentation.slides.append(slide)
            if slide.topic not in self.current_presentation.topics_covered:
                self.current_presentation.topics_covered.append(slide.topic)

    def save_presentation(self):
        """Save the current presentation to disk"""
        if self.current_presentation:
            pres_file = PRESENTATIONS_DIR / f"{self.current_presentation.id}.json"
            pres_data = {
                'id': self.current_presentation.id,
                'name': self.current_presentation.name,
                'created_at': self.current_presentation.created_at,
                'topics_covered': self.current_presentation.topics_covered,
                'slide_count': len(self.current_presentation.slides),
                'slides': [asdict(s) for s in self.current_presentation.slides[-100:]]  # Keep last 100
            }
            with open(pres_file, 'w', encoding='utf-8') as f:
                json.dump(pres_data, f, indent=2)

    def get_statistics(self) -> Dict:
        """Get statistics about stored data"""
        return {
            'total_content_items': len(self.content_cache),
            'total_images': len(self.get_all_images()),
            'queue_size': self.get_queue_size(),
            'topics': list(set(c.get('topic', '') for c in self.content_cache.values())),
            'presentations_saved': len(list(PRESENTATIONS_DIR.glob("*.json")))
        }


# Test
if __name__ == "__main__":
    dm = DataManager()
    stats = dm.get_statistics()
    print(f"Data Manager Stats: {stats}")
