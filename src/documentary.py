"""
Chess Documentary - Cinematic Mode Launcher
A visual journey through chess history and AI
"""
import sys
import threading
import time
import argparse
import signal
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_SPEED, HISTORICAL_TOPICS, IMAGE_SEARCH_TOPICS, calculate_delay
from web_search import WebSearcher
from data_manager import DataManager
from cinematic import CinematicOverlay


class DocumentaryEngine:
    """
    Orchestrates the chess documentary experience
    Continuously fetches historical content and displays it cinematically
    """

    def __init__(self, speed: int = DEFAULT_SPEED):
        self.speed = speed
        self.running = False
        self.searcher = WebSearcher()
        self.data_manager = DataManager()
        self.overlay: CinematicOverlay = None

        # Override topics with historical ones
        self.searcher.topic_index = 0
        self.topics = HISTORICAL_TOPICS.copy()
        self.image_topics = IMAGE_SEARCH_TOPICS.copy()

        # Stats
        self.images_fetched = 0
        self.content_fetched = 0

    def _fetch_content_worker(self):
        """Background worker for fetching content"""
        print("[Documentary] Content worker started")

        while self.running:
            try:
                # Fetch historical content
                topic = self.topics[self.searcher.topic_index % len(self.topics)]
                self.searcher.topic_index += 1

                print(f"\n[Fetching] {topic}")

                # Update overlay topic
                if self.overlay:
                    self.overlay.root.after(0, lambda t=topic: self.overlay.update_topic(t))

                # Fetch content
                content_items = self.searcher.fetch_topic_content(topic)
                for content in content_items[:2]:
                    self.data_manager.add_content(asdict(content))
                    self.content_fetched += 1
                    print(f"  [+] {content.title[:50]}...")

                # Also fetch images specifically
                img_topic = self.image_topics[self.images_fetched % len(self.image_topics)]
                images = self.searcher.search_images(img_topic, max_results=5)
                if images:
                    self.searcher._download_search_images(images, img_topic)
                    self.images_fetched += len(images)
                    print(f"  [img] Downloaded {len(images)} images for: {img_topic}")

                time.sleep(15)  # Wait between fetches

            except Exception as e:
                print(f"[Documentary] Fetch error: {e}")
                time.sleep(5)

        print("[Documentary] Content worker stopped")

    def _on_need_content(self):
        """Callback when overlay needs content"""
        pass  # Content worker handles this continuously

    def _initial_content_load(self):
        """Load some initial content before starting"""
        print("\n=== Loading Initial Content ===")

        # Check for cached content
        cached = len(self.data_manager.content_cache)
        print(f"Found {cached} cached content items")

        # Fetch some fresh content
        for topic in self.topics[:2]:
            print(f"Fetching: {topic}")
            try:
                content = self.searcher.fetch_topic_content(topic)
                for c in content[:2]:
                    self.data_manager.add_content(asdict(c))
                    print(f"  [+] {c.title[:50]}...")
            except Exception as e:
                print(f"  [!] Error: {e}")

        # Fetch some images
        for img_topic in self.image_topics[:3]:
            print(f"Fetching images: {img_topic}")
            try:
                images = self.searcher.search_images(img_topic, max_results=5)
                if images:
                    self.searcher._download_search_images(images, img_topic)
                    print(f"  [+] {len(images)} images")
            except Exception as e:
                print(f"  [!] Error: {e}")

        print("=== Initial Load Complete ===\n")

    def start(self):
        """Start the documentary experience"""
        print("""
+================================================================+
|                                                                |
|     CHESS: A DOCUMENTARY                                       |
|     The History of Chess & Artificial Intelligence             |
|                                                                |
|     Controls:                                                  |
|       [SPACE]  - Pause/Resume                                  |
|       [<-][->] - Adjust speed                                  |
|       [ESC][Q] - Exit                                          |
|                                                                |
+================================================================+
        """)

        self.running = True

        # Load initial content
        self._initial_content_load()

        # Create overlay
        self.overlay = CinematicOverlay(
            data_manager=self.data_manager,
            on_need_content=self._on_need_content
        )
        self.overlay.speed = self.speed

        # Start content worker
        content_thread = threading.Thread(target=self._fetch_content_worker, daemon=True)
        content_thread.start()

        # Start overlay (blocks)
        try:
            self.overlay.start()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop the documentary"""
        print("\n[Documentary] Shutting down...")
        self.running = False

        stats = self.data_manager.get_statistics()
        print(f"""
=== Session Statistics ===
Content Fetched: {self.content_fetched}
Images Fetched: {self.images_fetched}
Total Cached: {stats.get('total_content_items', 0)}
Total Images: {stats.get('total_images', 0)}
==========================
        """)


def main():
    parser = argparse.ArgumentParser(
        description="Chess Documentary - A cinematic journey through chess history"
    )
    parser.add_argument(
        '-s', '--speed',
        type=int,
        default=DEFAULT_SPEED,
        help=f'Animation speed (1-200, default: {DEFAULT_SPEED})'
    )

    args = parser.parse_args()
    speed = max(1, min(200, args.speed))

    def signal_handler(sig, frame):
        print("\nInterrupted")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    engine = DocumentaryEngine(speed=speed)
    engine.start()


if __name__ == "__main__":
    main()
