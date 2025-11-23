"""
Full-Screen Presentation Engine
Displays chess learning content in an infinite presentation loop
"""
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageTk
import threading
import queue
import time
import textwrap
from typing import Optional, Callable
from dataclasses import dataclass

from config import (
    BACKGROUND_COLOR, TEXT_COLOR, ACCENT_COLOR, SECONDARY_COLOR,
    PRESENTATION_TITLE, DEFAULT_SPEED, calculate_delay
)
from data_manager import Slide


class PresentationEngine:
    """Full-screen presentation engine with speed control"""

    def __init__(self, on_need_content: Callable = None):
        self.root = None
        self.running = False
        self.paused = False
        self.speed = DEFAULT_SPEED
        self.current_slide: Optional[Slide] = None
        self.slide_queue = queue.Queue()
        self.on_need_content = on_need_content

        # UI elements
        self.canvas = None
        self.title_label = None
        self.content_frame = None
        self.image_label = None
        self.status_label = None
        self.speed_label = None
        self.progress_bar = None

        # Image cache
        self.current_image = None
        self.photo_image = None

        # Threading
        self.presentation_thread = None
        self.content_thread = None

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
        self.title_font = tkfont.Font(family="Segoe UI", size=42, weight="bold")
        self.content_font = tkfont.Font(family="Segoe UI", size=24)
        self.small_font = tkfont.Font(family="Segoe UI", size=14)
        self.topic_font = tkfont.Font(family="Segoe UI", size=18, slant="italic")

        # Main container
        self.main_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Header with title and controls
        self.header_frame = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.header_frame.pack(fill=tk.X, pady=(0, 20))

        # App title
        app_title = tk.Label(
            self.header_frame,
            text="♔ ChessMaster Learning System ♔",
            font=tkfont.Font(family="Segoe UI", size=20, weight="bold"),
            fg=ACCENT_COLOR,
            bg=BACKGROUND_COLOR
        )
        app_title.pack(side=tk.LEFT)

        # Speed control frame
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
            text="● RUNNING",
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
            text="Topic: Loading...",
            font=self.topic_font,
            fg=ACCENT_COLOR,
            bg=SECONDARY_COLOR,
            anchor="w"
        )
        self.topic_label.pack(fill=tk.X, padx=30, pady=(30, 10))

        # Title
        self.title_label = tk.Label(
            self.text_frame,
            text="Loading...",
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
            text="Searching the web for chess content...",
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
            text="♞",
            font=tkfont.Font(family="Segoe UI", size=200),
            fg=ACCENT_COLOR,
            bg=SECONDARY_COLOR
        )
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Footer with progress
        self.footer_frame = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.footer_frame.pack(fill=tk.X, pady=(20, 0))

        # Progress info
        self.progress_label = tk.Label(
            self.footer_frame,
            text="Slides: 0 | Queue: 0 | Topics: 0",
            font=self.small_font,
            fg="#6b7280",
            bg=BACKGROUND_COLOR
        )
        self.progress_label.pack(side=tk.LEFT)

        # Delay indicator
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
            self.status_label.config(text="● PAUSED", fg="#fbbf24")
        else:
            self.status_label.config(text="● RUNNING", fg="#4ade80")

    def add_slide(self, slide: Slide):
        """Add a slide to the queue"""
        self.slide_queue.put(slide)

    def display_slide(self, slide: Slide):
        """Display a slide on screen"""
        if not self.root:
            return

        self.current_slide = slide

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
            # Truncate URL for display
            url = slide.source_url
            if len(url) > 80:
                url = url[:77] + "..."
            source_text = f"Source: {url}"
        self.source_label.config(text=source_text)

        # Update image
        self._display_image(slide.images[0] if slide.images else None)

        # Force update
        self.root.update_idletasks()

    def _display_image(self, image_path: str = None):
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

        # Show chess piece placeholder
        pieces = ["♔", "♕", "♖", "♗", "♘", "♙", "♚", "♛", "♜", "♝", "♞", "♟"]
        import random
        self.image_label.config(
            image="",
            text=random.choice(pieces),
            font=tkfont.Font(family="Segoe UI", size=200)
        )

    def update_progress(self, slides_shown: int, queue_size: int, topics_count: int):
        """Update progress display"""
        if self.progress_label:
            self.progress_label.config(
                text=f"Slides: {slides_shown} | Queue: {queue_size} | Topics: {topics_count}"
            )

    def _presentation_loop(self):
        """Main presentation loop running in separate thread"""
        slides_shown = 0

        while self.running:
            # Check if paused
            while self.paused and self.running:
                time.sleep(0.1)

            if not self.running:
                break

            # Get next slide
            try:
                slide = self.slide_queue.get(timeout=0.5)

                # Schedule UI update on main thread
                if self.root:
                    self.root.after(0, lambda s=slide: self.display_slide(s))

                slides_shown += 1

                # Update progress
                if self.root:
                    self.root.after(0, lambda: self.update_progress(
                        slides_shown,
                        self.slide_queue.qsize(),
                        0
                    ))

                # Wait based on speed
                delay = calculate_delay(self.speed)
                time.sleep(delay)

            except queue.Empty:
                # Request more content
                if self.on_need_content:
                    self.on_need_content()
                time.sleep(0.5)

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
    def need_content():
        print("Need more content!")

    engine = PresentationEngine(on_need_content=need_content)

    # Add test slides
    test_slide = Slide(
        id="test1",
        title="Welcome to Chess Learning",
        content="Chess is a two-player strategy board game played on a checkered board with 64 squares arranged in an 8×8 grid. The game is played by millions of people worldwide.",
        excerpts=[],
        images=[],
        source_url="https://example.com",
        topic="chess basics",
        slide_type="content"
    )
    engine.add_slide(test_slide)

    engine.start()
