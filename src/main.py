"""
ChessMaster - Main Orchestrator
Coordinates web searching, content processing, and presentation
"""
import sys
import threading
import time
import argparse
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_SPEED, CHESS_TOPICS, calculate_delay
from web_search import WebSearcher, ContentItem
from data_manager import DataManager, Slide
from presentation import PresentationEngine


class ChessMaster:
    """Main orchestrator for the Chess Learning Presentation System"""

    def __init__(self, speed: int = DEFAULT_SPEED):
        self.speed = speed
        self.running = False
        self.searcher = WebSearcher()
        self.data_manager = DataManager()
        self.presentation: PresentationEngine = None

        # Threading
        self.content_thread = None
        self.min_queue_size = 10  # Minimum slides to keep queued

        # Statistics
        self.slides_generated = 0
        self.topics_searched = 0
        self.content_fetched = 0

    def _content_worker(self):
        """Background worker that continuously fetches new content"""
        print("Content worker started...")

        while self.running:
            try:
                # Check if we need more slides
                if self.presentation and self.presentation.slide_queue.qsize() < self.min_queue_size:
                    self._fetch_and_queue_content()
                else:
                    time.sleep(1)  # Wait before checking again
            except Exception as e:
                print(f"Content worker error: {e}")
                time.sleep(2)

        print("Content worker stopped.")

    def _fetch_and_queue_content(self):
        """Fetch new content and add slides to queue"""
        topic = self.searcher.get_next_topic()
        print(f"\n[Fetching] {topic}")
        self.topics_searched += 1

        try:
            content_items = self.searcher.fetch_topic_content(topic)

            for content in content_items:
                # Add to data manager
                from dataclasses import asdict
                self.data_manager.add_content(asdict(content))
                self.content_fetched += 1

                # Create and queue slides
                slides = self.data_manager.create_slides_from_content(asdict(content))
                for slide in slides:
                    if self.presentation:
                        self.presentation.add_slide(slide)
                        self.slides_generated += 1

                print(f"  [+] {content.title[:50]}... ({len(slides)} slides)")

        except Exception as e:
            print(f"Error fetching content: {e}")

        # Also check for existing content to re-queue
        if self.presentation and self.presentation.slide_queue.qsize() < 5:
            self._queue_existing_content()

    def _queue_existing_content(self):
        """Queue slides from existing cached content"""
        content = self.data_manager.get_random_content()
        if content:
            slides = self.data_manager.create_slides_from_content(content)
            for slide in slides:
                if self.presentation:
                    self.presentation.add_slide(slide)
                    self.slides_generated += 1

    def _on_need_content(self):
        """Callback when presentation needs more content"""
        if self.running:
            # First, try to queue existing content quickly
            self._queue_existing_content()

    def _initial_content_load(self):
        """Load initial content before starting presentation"""
        print("\n=== Loading Initial Content ===")

        # First, queue any existing cached content
        existing_count = 0
        for content_id, content in list(self.data_manager.content_cache.items())[:5]:
            slides = self.data_manager.create_slides_from_content(content)
            for slide in slides:
                self.presentation.add_slide(slide)
                existing_count += 1

        if existing_count > 0:
            print(f"Queued {existing_count} slides from cached content")

        # Fetch some fresh content
        print("Fetching fresh content from the web...")
        for i in range(2):  # Fetch 2 topics worth of content
            topic = self.searcher.get_next_topic()
            print(f"  Searching: {topic}")
            try:
                content_items = self.searcher.fetch_topic_content(topic)
                for content in content_items:
                    from dataclasses import asdict
                    self.data_manager.add_content(asdict(content))
                    slides = self.data_manager.create_slides_from_content(asdict(content))
                    for slide in slides:
                        self.presentation.add_slide(slide)
            except Exception as e:
                print(f"  Error: {e}")

        print(f"Initial queue size: {self.presentation.slide_queue.qsize()} slides")
        print("=== Starting Presentation ===\n")

    def start(self):
        """Start the ChessMaster presentation system"""
        print("""
╔═══════════════════════════════════════════════════════════════╗
║           ♔ ChessMaster Learning System ♔                     ║
║                                                               ║
║  An infinite chess learning presentation system               ║
║                                                               ║
║  Controls:                                                    ║
║    Space     - Pause/Resume                                   ║
║    ←/→       - Adjust speed (±10)                             ║
║    ↑/↓       - Adjust speed (±25)                             ║
║    Esc / Q   - Exit                                           ║
║                                                               ║
║  Speed: 1 (slow) → 100 (default) → 200 (fast)                ║
╚═══════════════════════════════════════════════════════════════╝
        """)

        print(f"Starting with speed: {self.speed}")
        print(f"Estimated delay per slide: {calculate_delay(self.speed):.1f}s")
        print("")

        self.running = True

        # Create presentation engine
        self.presentation = PresentationEngine(on_need_content=self._on_need_content)
        self.presentation.speed = self.speed

        # Load initial content
        self._initial_content_load()

        # Start content worker thread
        self.content_thread = threading.Thread(target=self._content_worker, daemon=True)
        self.content_thread.start()

        # Start presentation (blocks until closed)
        try:
            self.presentation.start()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop the system"""
        print("\nShutting down ChessMaster...")
        self.running = False

        # Save presentation history
        self.data_manager.save_presentation()

        # Print statistics
        stats = self.data_manager.get_statistics()
        print(f"""
=== Session Statistics ===
Slides Generated: {self.slides_generated}
Topics Searched: {self.topics_searched}
Content Items Fetched: {self.content_fetched}
Total Cached Content: {stats['total_content_items']}
Total Images: {stats['total_images']}
========================
        """)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="ChessMaster - Infinite Chess Learning Presentation System"
    )
    parser.add_argument(
        '-s', '--speed',
        type=int,
        default=DEFAULT_SPEED,
        help=f'Presentation speed (1-200, default: {DEFAULT_SPEED}). '
             '1=very slow (~30s), 100=default (~5s), 200=fast (~0.2s)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode without web searching'
    )

    args = parser.parse_args()

    # Validate speed
    speed = max(1, min(200, args.speed))

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted by user")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start ChessMaster
    chess_master = ChessMaster(speed=speed)
    chess_master.start()


if __name__ == "__main__":
    main()
