"""
Full-Screen Presentation Engine
Displays chess lessons sequentially (no looping), with dynamic pacing
"""
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageTk
import threading
import time
import random
from typing import Optional, Callable, TYPE_CHECKING

from config import (
    BACKGROUND_COLOR, TEXT_COLOR, ACCENT_COLOR, SECONDARY_COLOR,
    PRESENTATION_TITLE, DEFAULT_SPEED, calculate_delay
)
from data_manager import Slide, Lesson

if TYPE_CHECKING:
    from data_manager import DataManager


class PresentationEngine:
    """Full-screen presentation engine - plays lessons sequentially"""

    def __init__(self, data_manager: 'DataManager', on_need_lesson: Callable = None):
        self.data_manager = data_manager
        self.on_need_lesson = on_need_lesson

        self.root = None
        self.running = False
        self.paused = False
        self.speed = DEFAULT_SPEED

        # Lesson tracking
        self.current_lesson: Optional[Lesson] = None
        self.current_slide_index = 0
        self.lessons_completed = 0
        self.total_slides_shown = 0

        self.waiting_for_content = False
        self.base_delay_multiplier = 1.0
        self.photo_image = None
        self.presentation_thread = None

    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title(PRESENTATION_TITLE)
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg=BACKGROUND_COLOR)

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Fonts
        self.title_font = tkfont.Font(family="Segoe UI", size=38, weight="bold")
        self.content_font = tkfont.Font(family="Segoe UI", size=22)
        self.small_font = tkfont.Font(family="Segoe UI", size=14)
        self.topic_font = tkfont.Font(family="Segoe UI", size=18, slant="italic")
        self.lesson_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")

        # Main container
        self.main_frame = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        # Header
        self.header_frame = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.header_frame.pack(fill=tk.X, pady=(0, 15))

        app_title = tk.Label(self.header_frame, text="ChessMaster Learning System",
            font=tkfont.Font(family="Segoe UI", size=20, weight="bold"),
            fg=ACCENT_COLOR, bg=BACKGROUND_COLOR)
        app_title.pack(side=tk.LEFT)

        self.lesson_label = tk.Label(self.header_frame, text="Preparing...",
            font=self.lesson_font, fg=TEXT_COLOR, bg=BACKGROUND_COLOR)
        self.lesson_label.pack(side=tk.LEFT, padx=50)

        # Controls
        self.control_frame = tk.Frame(self.header_frame, bg=BACKGROUND_COLOR)
        self.control_frame.pack(side=tk.RIGHT)

        self.speed_label = tk.Label(self.control_frame, text=f"Speed: {self.speed}",
            font=self.small_font, fg=TEXT_COLOR, bg=BACKGROUND_COLOR)
        self.speed_label.pack(side=tk.LEFT, padx=10)

        self.speed_slider = ttk.Scale(self.control_frame, from_=1, to=200,
            value=self.speed, orient=tk.HORIZONTAL, length=200,
            command=self._on_speed_change)
        self.speed_slider.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(self.control_frame, text="RUNNING",
            font=self.small_font, fg="#4ade80", bg=BACKGROUND_COLOR)
        self.status_label.pack(side=tk.LEFT, padx=20)

        # Content area
        self.content_container = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # Text frame (left)
        self.text_frame = tk.Frame(self.content_container, bg=SECONDARY_COLOR)
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))

        self.topic_label = tk.Label(self.text_frame, text="", font=self.topic_font,
            fg=ACCENT_COLOR, bg=SECONDARY_COLOR, anchor="w")
        self.topic_label.pack(fill=tk.X, padx=30, pady=(30, 10))

        self.title_label = tk.Label(self.text_frame, text="Welcome",
            font=self.title_font, fg=TEXT_COLOR, bg=SECONDARY_COLOR,
            wraplength=int(self.screen_width * 0.5), justify=tk.LEFT, anchor="nw")
        self.title_label.pack(fill=tk.X, padx=30, pady=(0, 20))

        separator = tk.Frame(self.text_frame, height=3, bg=ACCENT_COLOR)
        separator.pack(fill=tk.X, padx=30, pady=10)

        self.content_label = tk.Label(self.text_frame, text="Preparing lessons...",
            font=self.content_font, fg=TEXT_COLOR, bg=SECONDARY_COLOR,
            wraplength=int(self.screen_width * 0.5), justify=tk.LEFT, anchor="nw")
        self.content_label.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        self.source_label = tk.Label(self.text_frame, text="", font=self.small_font,
            fg="#6b7280", bg=SECONDARY_COLOR, anchor="w")
        self.source_label.pack(fill=tk.X, padx=30, pady=(0, 20))

        # Image frame (right)
        self.image_frame = tk.Frame(self.content_container, bg=SECONDARY_COLOR,
            width=int(self.screen_width * 0.35))
        self.image_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.image_frame.pack_propagate(False)

        self.image_label = tk.Label(self.image_frame, text="\u265E",
            font=tkfont.Font(family="Segoe UI", size=180),
            fg=ACCENT_COLOR, bg=SECONDARY_COLOR)
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Footer
        self.footer_frame = tk.Frame(self.main_frame, bg=BACKGROUND_COLOR)
        self.footer_frame.pack(fill=tk.X, pady=(20, 0))

        self.slide_progress_label = tk.Label(self.footer_frame, text="Slide: - / -",
            font=self.small_font, fg="#6b7280", bg=BACKGROUND_COLOR)
        self.slide_progress_label.pack(side=tk.LEFT)

        self.progress_label = tk.Label(self.footer_frame,
            text="Lessons: 0 | Queue: 0", font=self.small_font,
            fg="#6b7280", bg=BACKGROUND_COLOR)
        self.progress_label.pack(side=tk.LEFT, padx=50)

        self.delay_label = tk.Label(self.footer_frame,
            text=f"Delay: {calculate_delay(self.speed):.1f}s",
            font=self.small_font, fg="#6b7280", bg=BACKGROUND_COLOR)
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

        style = ttk.Style()
        style.configure("TScale", background=BACKGROUND_COLOR)

    def _on_speed_change(self, value):
        self.speed = int(float(value))
        self.speed_label.config(text=f"Speed: {self.speed}")
        self.delay_label.config(text=f"Delay: {calculate_delay(self.speed):.1f}s")

    def _adjust_speed(self, delta: int):
        new_speed = max(1, min(200, self.speed + delta))
        self.speed = new_speed
        self.speed_slider.set(new_speed)
        self._on_speed_change(new_speed)

    def toggle_pause(self):
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        color = "#fbbf24" if self.paused else "#4ade80"
        self.status_label.config(text=status, fg=color)

    def _skip_to_next_lesson(self):
        if self.current_lesson:
            print(f"[Skip] Skipping to next lesson...")
            self.current_slide_index = len(self.current_lesson.slides)

    def display_slide(self, slide: Slide, slide_num: int, total_slides: int):
        if not self.root:
            return

        self.topic_label.config(text=f"Topic: {slide.topic.title()}" if slide.topic else "")
        self.title_label.config(text=slide.title[:150] if slide.title else "Chess")

        content = slide.content[:800] + "..." if len(slide.content) > 800 else slide.content
        self.content_label.config(text=content)

        if slide.source_url:
            url = slide.source_url[:77] + "..." if len(slide.source_url) > 80 else slide.source_url
            self.source_label.config(text=f"Source: {url}")
        else:
            self.source_label.config(text="")

        self.slide_progress_label.config(text=f"Slide: {slide_num} / {total_slides}")
        self._display_image(slide.images[0] if slide.images else None, slide.slide_type)
        self.root.update_idletasks()

    def _display_image(self, image_path: str = None, slide_type: str = "content"):
        if image_path:
            try:
                img = Image.open(image_path)
                fw, fh = int(self.screen_width * 0.33), int(self.screen_height * 0.6)
                ratio = img.width / img.height
                if ratio > fw/fh:
                    nw, nh = fw, int(fw / ratio)
                else:
                    nh, nw = fh, int(fh * ratio)
                img = img.resize((nw, nh), Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.photo_image, text="")
                return
            except Exception as e:
                print(f"Image error: {e}")

        pieces = {'title': "\u265A", 'content': "\u265E", 'image': "\u265C",
                  'transition': "\u2026", 'summary': "\u2605"}
        self.image_label.config(image="", text=pieces.get(slide_type, "\u265F"),
            font=tkfont.Font(family="Segoe UI", size=180))

    def _show_waiting_screen(self):
        if not self.root:
            return
        self.topic_label.config(text="")
        self.title_label.config(text="Preparing Next Lesson...")
        self.content_label.config(text="Content is being fetched.\nNext lesson will start automatically.")
        self.source_label.config(text="")
        self.slide_progress_label.config(text="Slide: - / -")
        self.status_label.config(text="LOADING", fg="#fbbf24")
        self.image_label.config(image="", text="\u265A", font=tkfont.Font(family="Segoe UI", size=180))
        self.root.update_idletasks()

    def _update_progress(self):
        if self.progress_label:
            q = self.data_manager.presentation_queue.size
            self.progress_label.config(text=f"Lessons: {self.lessons_completed} | Queue: {q}")

    def _presentation_loop(self):
        """Main loop - sequential lesson playback"""
        print("[Presentation] Loop started")

        while self.running:
            # Handle pause
            while self.paused and self.running:
                time.sleep(0.1)

            if not self.running:
                break

            # Check if need next lesson
            need_next = (self.current_lesson is None or
                        self.current_slide_index >= len(self.current_lesson.slides))

            if need_next:
                # Complete current lesson
                old_id = self.current_lesson.id if self.current_lesson else None
                if self.current_lesson:
                    self.lessons_completed += 1
                    print(f"[DONE] Lesson {old_id[:8]} completed (#{self.lessons_completed})")
                    self.current_lesson = None

                if self.root:
                    self.root.after(0, self._update_progress)

                # Get next lesson
                qsize = self.data_manager.presentation_queue.size
                print(f"[GET] Fetching next lesson (queue: {qsize})...")
                next_lesson = self.data_manager.get_next_lesson(timeout=2.0)

                if next_lesson:
                    if old_id and next_lesson.id == old_id:
                        print(f"[BUG!] Same lesson {old_id[:8]} returned again!")
                    self.current_lesson = next_lesson
                    self.current_slide_index = 0
                    self.waiting_for_content = False
                    self.base_delay_multiplier = 1.0

                    print(f"[Presentation] STARTING: {next_lesson.title} ({len(next_lesson.slides)} slides)")

                    if self.root:
                        txt = f"Lesson {self.lessons_completed + 1}: {next_lesson.topic.title()}"
                        self.root.after(0, lambda t=txt: self.lesson_label.config(text=t))
                        self.root.after(0, lambda: self.status_label.config(text="RUNNING", fg="#4ade80"))
                else:
                    # No lesson available
                    print("[Presentation] No lesson available, showing waiting screen...")
                    self.waiting_for_content = True
                    self.base_delay_multiplier = 2.0

                    if self.root:
                        self.root.after(0, self._show_waiting_screen)
                    if self.on_need_lesson:
                        self.on_need_lesson()

                    time.sleep(1)
                    continue

            # Display current slide
            if self.current_lesson and self.current_slide_index < len(self.current_lesson.slides):
                slide = self.current_lesson.slides[self.current_slide_index]
                total = len(self.current_lesson.slides)
                idx = self.current_slide_index

                print(f"  [Slide {idx+1}/{total}] {slide.slide_type}: {slide.title[:40]}")

                if self.root:
                    self.root.after(0, lambda s=slide, n=idx+1, t=total: self.display_slide(s, n, t))

                self.current_slide_index += 1
                self.total_slides_shown += 1

                if self.root:
                    self.root.after(0, self._update_progress)

                delay = calculate_delay(self.speed) * self.base_delay_multiplier
                time.sleep(delay)

        print("[Presentation] Loop ended")

    def start(self):
        self.setup_ui()
        self.running = True
        self.presentation_thread = threading.Thread(target=self._presentation_loop, daemon=True)
        self.presentation_thread.start()
        self.root.mainloop()

    def stop(self):
        print("[Presentation] Stopping...")
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
