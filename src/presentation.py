"""
Full-Screen Presentation Engine
Displays chess lessons sequentially (no looping), with dynamic pacing
"""
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageTk
import threading
import queue
import time
import random
from typing import Optional, Callable, List
from dataclasses import dataclass

from config import (
    BACKGROUND_COLOR, TEXT_COLOR, ACCENT_COLOR, SECONDARY_COLOR,
    PRESENTATION_TITLE, DEFAULT_SPEED, calculate_delay
)
from data_manager import Slide, Lesson


class PresentationEngine:
    """Full-screen presentation engine with lesson-based sequential playback"""

    def __init__(self, on_need_lesson: Callable = None):
        self.root = None
        self.running = False
        self.paused = False
        self.speed = DEFAULT_SPEED
        self.on_need_lesson = on_need_lesson

        # Lesson management
        self.lesson_queue: queue.Queue[Lesson] = queue.Queue()
        self.current_lesson: Optional[Lesson] = None
        self.current_slide_index = 0
        self.lessons_completed = 0
        self.total_slides_shown = 0

        # State tracking
        self.waiting_for_content = False
        self.base_delay_multiplier = 1.0  # Can increase when waiting

        # UI elements
        self.canvas = None
        self.title_label = None
        self.content_label = None
        self.image_label = None
        self.status_label = None
        self.speed_label = None
        self.lesson_label = None
        self.progress_label = None

        # Image cache
        self.photo_image = None

        # Threading
        self.presentation_thread = None

    def setup_ui(self):
        """Initialize the tkinter UI"""
        self.root = tk.Tk()
        self.root.title(PRESENTATION_TITLE)

        # Full screen
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg=BACKGROUND_COLOR)

        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Custom fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=38, weight="bold")
        self.content_font = tkfont.Font(family="Segoe UI", size=22)
        self.small_font = tkfont.Font(family="Segoe UI", size=14)
        self.topic_font = tkfont.Font(family="Segoe UI", size=18, slant="italic")
        self.lesson_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")

        # Main container
        self.main_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Header with title and controls
        self.header_frame = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.header_frame.pack(fill=tk.X, pady=(0, 15))

        # App title
        app_title = tk.Label(
            self.header_frame,
            text="ChessMaster Learning System",
            font=tkfont.Font(family="Segoe UI", size=20, weight="bold"),
            fg=ACCENT_COLOR,
            bg=BACKGROUND_COLOR
        )
        app_title.pack(side=tk.LEFT)

        # Lesson info (center)
        self.lesson_label = tk.Label(
            self.header_frame,
            text="Preparing first lesson...",
            font=self.lesson_font,
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR
        )
        self.lesson_label.pack(side=tk.LEFT, padx=50)

        # Speed control frame (right)
        self.control_frame = tk.Frame(self.header_frame, bg=BACKGROUND_COLOR)
        self.control_frame.pack(side=tk.RIGHT)

        # Speed label
        self.speed_label = tk.Label(
            self.control_frame,
            text=f"Speed: {self.speed}",
            font=self.small_font,
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR
        )
        self.speed_label.pack(side=tk.LEFT, padx=10)

        # Speed slider
        self.speed_slider = ttk.Scale(
            self.control_frame,
            from_=1,
            to=200,
            value=self.speed,
            orient=tk.HORIZONTAL,
            length=200,
            command=self._on_speed_change
        )
        self.speed_slider.pack(side=tk.LEFT, padx=10)

        # Status indicator
        self.status_label = tk.Label(
            self.control_frame,
            text="RUNNING",
            font=self.small_font,
            fg="#4ade80",
            bg=BACKGROUND_COLOR
        )
        self.status_label.pack(side=tk.LEFT, padx=20)

        # Content area - split into text and image
        self.content_container = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # Left side - Text content (60%)
        self.text_frame = tk.Frame(self.content_container, bg=SECONDARY_COLOR)
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))

        # Topic label
        self.topic_label = tk.Label(
            self.text_frame,
            text="",
            font=self.topic_font,
            fg=ACCENT_COLOR,
            bg=SECONDARY_COLOR,
            anchor="w"
        )
        self.topic_label.pack(fill=tk.X, padx=30, pady=(30, 10))

        # Title
        self.title_label = tk.Label(
            self.text_frame,
            text="Welcome to ChessMaster",
            font=self.title_font,
            fg=TEXT_COLOR,
            bg=SECONDARY_COLOR,
            wraplength=int(self.screen_width * 0.5),
            justify=tk.LEFT,
            anchor="nw"
        )
        self.title_label.pack(fill=tk.X, padx=30, pady=(0, 20))

        # Separator
        separator = tk.Frame(self.text_frame, height=3, bg=ACCENT_COLOR)
        separator.pack(fill=tk.X, padx=30, pady=10)

        # Content text
        self.content_label = tk.Label(
            self.text_frame,
            text="Preparing your chess lessons...\n\nContent is being fetched from the web.",
            font=self.content_font,
            fg=TEXT_COLOR,
            bg=SECONDARY_COLOR,
            wraplength=int(self.screen_width * 0.5),
            justify=tk.LEFT,
            anchor="nw"
        )
        self.content_label.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        # Source URL
        self.source_label = tk.Label(
            self.text_frame,
            text="",
            font=self.small_font,
            fg="#6b7280",
            bg=SECONDARY_COLOR,
            anchor="w"
        )
        self.source_label.pack(fill=tk.X, padx=30, pady=(0, 20))

        # Right side - Image (40%)
        self.image_frame = tk.Frame(
            self.content_container,
            bg=SECONDARY_COLOR,
            width=int(self.screen_width * 0.35)
        )
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.image_frame.pack_propagate(False)

        # Image display
        self.image_label = tk.Label(
            self.image_frame,
            text="♔",
            font=tkfont.Font(family="Segoe UI", size=180),
            fg=ACCENT_COLOR,
            bg=SECONDARY_COLOR
        )
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Footer with progress
        self.footer_frame = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.footer_frame.pack(fill=tk.X, pady=(20, 0))

        # Slide progress (left)
        self.slide_progress_label = tk.Label(
            self.footer_frame,
            text="Slide: - / -",
            font=self.small_font,
            fg="#6b7280",
            bg=BACKGROUND_COLOR
        )
        self.slide_progress_label.pack(side=tk.LEFT)

        # Overall progress (center)
        self.progress_label = tk.Label(
            self.footer_frame,
            text="Lessons: 0 | Queue: 0 | Total slides: 0",
            font=self.small_font,
            fg="#6b7280",
            bg=BACKGROUND_COLOR
        )
        self.progress_label.pack(side=tk.LEFT, padx=50)

        # Delay indicator (right)
        self.delay_label = tk.Label(
            self.footer_frame,
            text=f"Delay: {calculate_delay(self.speed):.1f}s",
            font=self.small_font,
            fg="#6b7280",
            bg=BACKGROUND_COLOR
        )
        self.delay_label.pack(side=tk.RIGHT)

        # Key bindings
        self.root.bind('<Escape>', lambda e: self.stop())
        self.root.bind('<space>', lambda e: self.toggle_pause())
        self.root.bind('<Left>', lambda e: self._adjust_speed(-10))
        self.root.bind('<Right>', lambda e: self._adjust_speed(10))
        self.root.bind('<Up>', lambda e: self._adjust_speed(25))
        self.root.bind('<Down>', lambda e: self._adjust_speed(-25))
        self.root.bind('q', lambda e: self.stop())
        self.root.bind('Q', lambda e: self.stop())
        self.root.bind('n', lambda e: self._skip_to_next_lesson())
        self.root.bind('N', lambda e: self._skip_to_next_lesson())

        # Style for slider
        style = ttk.Style()
        style.configure("TScale", background=BACKGROUND_COLOR)

    def _on_speed_change(self, value):
        """Handle speed slider change"""
        self.speed = int(float(value))
        self.speed_label.config(text=f"Speed: {self.speed}")
        self.delay_label.config(text=f"Delay: {calculate_delay(self.speed):.1f}s")

    def _adjust_speed(self, delta: int):
        """Adjust speed by delta"""
        new_speed = max(1, min(200, self.speed + delta))
        self.speed = new_speed
        self.speed_slider.set(new_speed)
        self._on_speed_change(new_speed)

    def toggle_pause(self):
        """Toggle pause state"""
        self.paused = not self.paused
        if self.paused:
            self.status_label.config(text="PAUSED", fg="#fbbf24")
        else:
            self.status_label.config(text="RUNNING", fg="#4ade80")

    def _skip_to_next_lesson(self):
        """Skip to the next lesson"""
        if self.current_lesson:
            self.current_slide_index = len(self.current_lesson.slides)

    def queue_lesson(self, lesson: Lesson):
        """Add a lesson to the queue"""
        self.lesson_queue.put(lesson)
        self._update_waiting_state()

    def _update_waiting_state(self):
        """Update waiting state based on queue"""
        was_waiting = self.waiting_for_content
        self.waiting_for_content = (
            self.lesson_queue.empty() and
            (self.current_lesson is None or
             self.current_slide_index >= len(self.current_lesson.slides))
        )

        if self.waiting_for_content and not was_waiting:
            self.base_delay_multiplier = 2.0  # Slow down when waiting
        elif not self.waiting_for_content and was_waiting:
            self.base_delay_multiplier = 1.0  # Return to normal

    def display_slide(self, slide: Slide, slide_num: int, total_slides: int):
        """Display a slide on screen"""
        if not self.root:
            return

        # Update topic
        topic_text = f"Topic: {slide.topic.title()}" if slide.topic else ""
        self.topic_label.config(text=topic_text)

        # Update title
        title = slide.title[:150] if slide.title else "Chess Content"
        self.title_label.config(text=title)

        # Update content
        content = slide.content
        if len(content) > 800:
            content = content[:800] + "..."
        self.content_label.config(text=content)

        # Update source
        source_text = ""
        if slide.source_url:
            url = slide.source_url
            if len(url) > 80:
                url = url[:77] + "..."
            source_text = f"Source: {url}"
        self.source_label.config(text=source_text)

        # Update slide progress
        self.slide_progress_label.config(text=f"Slide: {slide_num} / {total_slides}")

        # Update image
        self._display_image(slide.images[0] if slide.images else None, slide.slide_type)

        # Force update
        self.root.update_idletasks()

    def _display_image(self, image_path: str = None, slide_type: str = "content"):
        """Display an image or placeholder"""
        if image_path:
            try:
                img = Image.open(image_path)

                # Calculate size to fit frame
                frame_width = int(self.screen_width * 0.33)
                frame_height = int(self.screen_height * 0.6)

                # Maintain aspect ratio
                img_ratio = img.width / img.height
                frame_ratio = frame_width / frame_height

                if img_ratio > frame_ratio:
                    new_width = frame_width
                    new_height = int(frame_width / img_ratio)
                else:
                    new_height = frame_height
                    new_width = int(frame_height * img_ratio)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.photo_image, text="")
                return
            except Exception as e:
                print(f"Error loading image: {e}")

        # Show chess piece placeholder based on slide type
        pieces = {
            'title': ["♔", "♚"],
            'content': ["♕", "♛", "♖", "♜", "♗", "♝"],
            'image': ["♘", "♞"],
            'transition': ["..."],
            'summary': ["♔", "♚"],
        }
        piece_list = pieces.get(slide_type, ["♙", "♟"])
        self.image_label.config(
            image="",
            text=random.choice(piece_list),
            font=tkfont.Font(family="Segoe UI", size=180)
        )

    def _show_waiting_screen(self):
        """Show a waiting screen while content is being generated"""
        if not self.root:
            return

        self.topic_label.config(text="")
        self.title_label.config(text="Preparing Next Lesson...")
        self.content_label.config(
            text="Content is being fetched from the web.\n\n"
                 "The next lesson will begin automatically when ready.\n\n"
                 "This system continuously searches for new chess content\n"
                 "to provide you with fresh learning material."
        )
        self.source_label.config(text="")
        self.slide_progress_label.config(text="Slide: - / -")
        self.status_label.config(text="LOADING", fg="#fbbf24")

        # Animated waiting pieces
        pieces = ["♔", "♕", "♖", "♗", "♘", "♙"]
        self.image_label.config(
            image="",
            text=random.choice(pieces),
            font=tkfont.Font(family="Segoe UI", size=180)
        )

        self.root.update_idletasks()

    def _update_progress(self):
        """Update overall progress display"""
        if self.progress_label:
            self.progress_label.config(
                text=f"Lessons: {self.lessons_completed} | "
                     f"Queue: {self.lesson_queue.qsize()} | "
                     f"Total slides: {self.total_slides_shown}"
            )

    def _presentation_loop(self):
        """Main presentation loop - plays lessons sequentially"""
        while self.running:
            # Check if paused
            while self.paused and self.running:
                time.sleep(0.1)

            if not self.running:
                break

            # Get next lesson if needed
            if self.current_lesson is None or self.current_slide_index >= len(self.current_lesson.slides):
                # Current lesson is done, get next
                if self.current_lesson:
                    self.lessons_completed += 1
                    if self.root:
                        self.root.after(0, self._update_progress)

                try:
                    self.current_lesson = self.lesson_queue.get(timeout=0.5)
                    self.current_slide_index = 0

                    # Update lesson label
                    if self.root and self.current_lesson:
                        lesson_text = f"Lesson {self.lessons_completed + 1}: {self.current_lesson.topic.title()}"
                        self.root.after(0, lambda t=lesson_text: self.lesson_label.config(text=t))
                        self.root.after(0, lambda: self.status_label.config(text="RUNNING", fg="#4ade80"))

                except queue.Empty:
                    # No lessons available, show waiting and request more
                    self._update_waiting_state()
                    if self.root:
                        self.root.after(0, self._show_waiting_screen)
                    if self.on_need_lesson:
                        self.on_need_lesson()
                    time.sleep(1)  # Wait a bit before checking again
                    continue

            # Display current slide
            if self.current_lesson and self.current_slide_index < len(self.current_lesson.slides):
                slide = self.current_lesson.slides[self.current_slide_index]
                total_slides = len(self.current_lesson.slides)

                if self.root:
                    self.root.after(0, lambda s=slide, n=self.current_slide_index+1, t=total_slides:
                                   self.display_slide(s, n, t))

                self.current_slide_index += 1
                self.total_slides_shown += 1

                if self.root:
                    self.root.after(0, self._update_progress)

                # Calculate delay based on speed and waiting state
                delay = calculate_delay(self.speed) * self.base_delay_multiplier
                time.sleep(delay)

    def start(self):
        """Start the presentation"""
        self.setup_ui()
        self.running = True

        # Start presentation thread
        self.presentation_thread = threading.Thread(target=self._presentation_loop, daemon=True)
        self.presentation_thread.start()

        # Start main loop
        self.root.mainloop()

    def stop(self):
        """Stop the presentation"""
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None


# Test
if __name__ == "__main__":
    def need_lesson():
        print("Need more lessons!")

    engine = PresentationEngine(on_need_lesson=need_lesson)

    # Add test lesson
    test_slides = [
        Slide(
            id="test1",
            title="Welcome to Chess",
            content="Chess is a game of strategy.",
            excerpts=[],
            images=[],
            source_url="",
            topic="chess basics",
            slide_type="title"
        ),
        Slide(
            id="test2",
            title="The Board",
            content="The chess board has 64 squares.",
            excerpts=[],
            images=[],
            source_url="",
            topic="chess basics",
            slide_type="content"
        ),
    ]

    test_lesson = Lesson(
        id="test",
        title="Test Lesson",
        topic="chess basics",
        slides=test_slides,
        created_at="",
        source_urls=[],
        estimated_duration=10.0
    )
    engine.queue_lesson(test_lesson)
    engine.start()
