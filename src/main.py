"""
ChessMaster - Main Orchestrator
Coordinates web searching, content processing, and presentation
Supports continuous background lesson generation and sequential playback
"""
import sys
import threading
import time
import argparse
import signal
from pathlib import Path
from dataclasses import asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_SPEED, CHESS_TOPICS, calculate_delay
from web_search import WebSearcher, ContentItem
from data_manager import DataManager, Lesson
from presentation import PresentationEngine


class LessonBuilder:
    """
    Background worker that continuously builds lessons ahead of time.
    Takes advantage of any available time to pre-generate content.
    """

    def __init__(self, searcher: WebSearcher, data_manager: DataManager):
        self.searcher = searcher
        self.data_manager = data_manager
        self.running = False
        self.thread = None

        # Configuration
        self.min_queue_size = 3  # Minimum lessons to keep queued
        self.max_queue_size = 10  # Maximum lessons to queue
        self.content_per_lesson = 2  # Content items per lesson

        # Statistics
        self.lessons_built = 0
        self.content_fetched = 0
        self.topics_searched = 0

    def start(self):
        """Start the background lesson builder"""
        self.running = True
        self.thread = threading.Thread(target=self._build_loop, daemon=True)
        self.thread.start()
        print("[LessonBuilder] Started background lesson generation")

    def stop(self):
        """Stop the lesson builder"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[LessonBuilder] Stopped")

    def _build_loop(self):
        """Main loop that continuously builds lessons"""
        while self.running:
            try:
                queue_size = self.data_manager.presentation_queue.size

                # Always try to maintain minimum queue
                if queue_size < self.min_queue_size:
                    self._build_lesson()
                # If under max, build more but slower
                elif queue_size < self.max_queue_size:
                    time.sleep(2)  # Brief pause
                    self._build_lesson()
                else:
                    # Queue is full, wait before checking again
                    time.sleep(5)

            except Exception as e:
                print(f"[LessonBuilder] Error: {e}")
                time.sleep(3)

    def _build_lesson(self):
        """Build a single lesson by fetching content and creating slides"""
        topic = self.searcher.get_next_topic()
        print(f"\n[LessonBuilder] Building lesson: {topic}")
        self.topics_searched += 1

        content_items = []

        # Fetch content from web
        try:
            fetched = self.searcher.fetch_topic_content(topic)
            for content in fetched[:self.content_per_lesson]:
                content_dict = asdict(content)
                self.data_manager.add_content(content_dict)
                content_items.append(content_dict)
                self.content_fetched += 1
                print(f"  [+] Fetched: {content.title[:50]}...")
        except Exception as e:
            print(f"  [!] Fetch error: {e}")

        # If we didn't get enough from web, use cached content
        while len(content_items) < self.content_per_lesson:
            cached = self.data_manager.get_unused_content()
            if cached:
                content_items.append(cached)
                print(f"  [+] Using cached: {cached.get('title', 'Unknown')[:50]}...")
            else:
                break

        # Build and queue the lesson
        if content_items:
            lesson = self.data_manager.build_lesson(content_items, topic)
            self.data_manager.queue_lesson(lesson)
            self.lessons_built += 1
            print(f"  [=] Lesson queued: {len(lesson.slides)} slides, ~{lesson.estimated_duration:.0f}s")
        else:
            print(f"  [!] No content available for lesson")

    def get_stats(self) -> dict:
        """Get builder statistics"""
        return {
            'lessons_built': self.lessons_built,
            'content_fetched': self.content_fetched,
            'topics_searched': self.topics_searched,
            'queue_size': self.data_manager.presentation_queue.size
        }


class ChessMaster:
    """Main orchestrator for the Chess Learning Presentation System"""

    def __init__(self, speed: int = DEFAULT_SPEED):
        self.speed = speed
        self.running = False
        self.searcher = WebSearcher()
        self.data_manager = DataManager()
        self.lesson_builder: LessonBuilder = None
        self.presentation: PresentationEngine = None

    def _on_need_lesson(self):
        """Callback when presentation needs more lessons"""
        # The lesson builder runs continuously, so this is mainly for logging
        queue_status = self.data_manager.get_queue_status()
        if queue_status['is_empty']:
            print("[ChessMaster] Waiting for next lesson to be built...")

    def _initial_lesson_build(self):
        """Build initial lessons before starting presentation"""
        print("\n=== Building Initial Lessons ===")

        # First check for existing cached content
        cached_count = len(self.data_manager.content_cache)
        if cached_count > 0:
            print(f"Found {cached_count} cached content items")

            # Build a lesson from cached content immediately
            content_items = []
            for _ in range(2):
                cached = self.data_manager.get_unused_content()
                if cached:
                    content_items.append(cached)

            if content_items:
                lesson = self.data_manager.build_lesson(
                    content_items,
                    content_items[0].get('topic', 'chess basics')
                )
                self.data_manager.queue_lesson(lesson)
                print(f"  [+] Built lesson from cache: {len(lesson.slides)} slides")

        # Fetch fresh content for first lesson
        print("Fetching fresh content from the web...")
        topic = self.searcher.get_next_topic()
        print(f"  Searching: {topic}")

        try:
            content_items = self.searcher.fetch_topic_content(topic)
            if content_items:
                content_dicts = []
                for content in content_items[:2]:
                    content_dict = asdict(content)
                    self.data_manager.add_content(content_dict)
                    content_dicts.append(content_dict)
                    print(f"    [+] {content.title[:50]}...")

                if content_dicts:
                    lesson = self.data_manager.build_lesson(content_dicts, topic)
                    self.data_manager.queue_lesson(lesson)
                    print(f"  [=] Built lesson: {len(lesson.slides)} slides")

        except Exception as e:
            print(f"  [!] Error: {e}")

        queue_size = self.data_manager.presentation_queue.size
        print(f"\nInitial lesson queue: {queue_size} lessons ready")
        print("=== Starting Presentation ===\n")

    def start(self):
        """Start the ChessMaster presentation system"""
        print("""
+===============================================================+
|           ChessMaster Learning System                         |
|                                                               |
|  Sequential chess lessons with continuous content generation  |
|                                                               |
|  Controls:                                                    |
|    Space     - Pause/Resume                                   |
|    Left/Right - Adjust speed (+/-10)                          |
|    Up/Down   - Adjust speed (+/-25)                           |
|    N         - Skip to next lesson                            |
|    Esc / Q   - Exit                                           |
|                                                               |
|  Speed: 1 (slow) -> 100 (default) -> 200 (fast)               |
+===============================================================+
        """)

        print(f"Starting with speed: {self.speed}")
        print(f"Estimated delay per slide: {calculate_delay(self.speed):.1f}s")
        print("")

        self.running = True

        # Create components
        self.lesson_builder = LessonBuilder(self.searcher, self.data_manager)
        self.presentation = PresentationEngine(on_need_lesson=self._on_need_lesson)
        self.presentation.speed = self.speed

        # Build initial lessons
        self._initial_lesson_build()

        # Start background lesson builder
        self.lesson_builder.start()

        # Connect presentation to lesson queue
        # The presentation will pull from data_manager.presentation_queue
        def queue_to_presentation():
            """Bridge: moves lessons from data_manager queue to presentation"""
            while self.running:
                try:
                    lesson = self.data_manager.get_next_lesson(timeout=1.0)
                    if lesson and self.presentation:
                        self.presentation.queue_lesson(lesson)
                        print(f"[Queue] Sent lesson to presentation: {lesson.title}")
                except Exception as e:
                    if self.running:
                        time.sleep(0.5)

        # Start queue bridge thread
        bridge_thread = threading.Thread(target=queue_to_presentation, daemon=True)
        bridge_thread.start()

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

        # Stop lesson builder
        if self.lesson_builder:
            self.lesson_builder.stop()

        # Print statistics
        dm_stats = self.data_manager.get_statistics()
        builder_stats = self.lesson_builder.get_stats() if self.lesson_builder else {}

        print(f"""
=== Session Statistics ===
Lessons Built: {builder_stats.get('lessons_built', 0)}
Lessons Completed: {dm_stats.get('lessons_played', 0)}
Content Items Fetched: {builder_stats.get('content_fetched', 0)}
Topics Searched: {builder_stats.get('topics_searched', 0)}
Total Cached Content: {dm_stats.get('total_content_items', 0)}
Total Images: {dm_stats.get('total_images', 0)}
Lessons Saved: {dm_stats.get('lessons_saved', 0)}
==========================
        """)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="ChessMaster - Sequential Chess Learning Presentation System"
    )
    parser.add_argument(
        '-s', '--speed',
        type=int,
        default=DEFAULT_SPEED,
        help=f'Presentation speed (1-200, default: {DEFAULT_SPEED}). '
             '1=very slow (~30s), 100=default (~5s), 200=fast (~0.2s)'
    )
    parser.add_argument(
        '--min-queue',
        type=int,
        default=3,
        help='Minimum lessons to keep in queue (default: 3)'
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
