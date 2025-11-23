"""
Cinematic Chess Documentary Overlay
A sci-fi indie film style presentation about chess history and AI
"""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
import threading
import time
import random
import math
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path

from config import calculate_delay, DEFAULT_SPEED, IMAGES_DIR


@dataclass
class FloatingElement:
    """An animated element on screen"""
    x: float
    y: float
    vx: float  # velocity x
    vy: float  # velocity y
    scale: float
    alpha: float
    rotation: float
    rotation_speed: float
    image: Optional[ImageTk.PhotoImage] = None
    text: str = ""
    element_type: str = "image"  # 'image', 'text', 'quote'
    lifetime: float = 30.0
    age: float = 0.0
    canvas_id: int = 0


@dataclass
class ScrollingText:
    """Horizontally or vertically scrolling text"""
    text: str
    x: float
    y: float
    speed: float
    font_size: int
    color: str
    direction: str  # 'left', 'right', 'up', 'down'
    canvas_id: int = 0


class CinematicOverlay:
    """
    Full-screen transparent overlay with animated chess content
    Like a documentary film playing over your desktop
    """

    def __init__(self, data_manager, on_need_content: Callable = None):
        self.data_manager = data_manager
        self.on_need_content = on_need_content

        self.root = None
        self.canvas = None
        self.running = False
        self.paused = False
        self.speed = DEFAULT_SPEED

        # Screen dimensions
        self.screen_width = 0
        self.screen_height = 0

        # Animated elements
        self.floating_elements: List[FloatingElement] = []
        self.scrolling_texts: List[ScrollingText] = []
        self.background_images: List[ImageTk.PhotoImage] = []

        # Content queue
        self.content_queue: List[dict] = []
        self.current_topic = "Chess History"
        self.quote_index = 0

        # Animation timing
        self.last_update = time.time()
        self.frame_time = 1/30  # 30 FPS

        # Threading
        self.animation_thread = None
        self.content_thread = None

        # Famous chess quotes for ambient text
        self.chess_quotes = [
            "Chess is life in miniature. - Garry Kasparov",
            "Every chess master was once a beginner. - Irving Chernev",
            "Chess is the gymnasium of the mind. - Blaise Pascal",
            "In chess, as in life, forethought wins. - Charles Buxton",
            "Chess is war over the board. - Bobby Fischer",
            "The beauty of chess is it can be whatever you want it to be. - Simon Williams",
            "Chess holds its master in its own bonds. - Albert Einstein",
            "Life is like chess, with struggle, competition, and good and bad events. - Benjamin Franklin",
            "Chess makes men wiser and clear-sighted. - Vladimir Putin",
            "I have come to the personal conclusion that chess is a waste of time. - Hikaru Nakamura",
            "Deep Blue vs Kasparov: The day machine challenged man. - 1997",
            "The Mechanical Turk: The first chess-playing 'automaton' - 1770",
            "AlphaZero: AI that mastered chess in 4 hours - 2017",
            "Stockfish: The strongest chess engine ever created",
        ]

        # Historical facts for scrolling
        self.historical_facts = [
            "570 AD - Chess originated in India as 'Chaturanga'",
            "1475 - The modern queen and bishop moves were established in Spain",
            "1770 - The Mechanical Turk 'automaton' amazed European courts",
            "1886 - Wilhelm Steinitz became the first official World Chess Champion",
            "1927 - Capablanca lost his title to Alekhine after 6 years of dominance",
            "1972 - Bobby Fischer defeated Boris Spassky in 'The Match of the Century'",
            "1985 - Garry Kasparov became the youngest World Champion at age 22",
            "1996 - Deep Blue became first computer to win a game against a reigning champion",
            "1997 - Deep Blue defeated Kasparov in a historic 6-game match",
            "2006 - Deep Fritz defeated Vladimir Kramnik 4-2",
            "2016 - Magnus Carlsen defended his title against Sergey Karjakin",
            "2017 - AlphaZero taught itself chess and defeated Stockfish 28-0",
            "2023 - AI engines now rate over 3500 Elo, far beyond any human",
        ]

    def setup_ui(self):
        """Create the transparent overlay window"""
        self.root = tk.Tk()
        self.root.title("Chess Documentary")

        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Make window fullscreen and transparent
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)

        # Platform-specific transparency
        try:
            # Windows transparency
            self.root.attributes('-alpha', 0.92)
            self.root.configure(bg='black')
            # Make black pixels transparent on Windows
            self.root.wm_attributes('-transparentcolor', 'black')
        except:
            self.root.configure(bg='#0a0a0a')

        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            bg='#0a0a0f',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Draw semi-transparent background gradient
        self._draw_background()

        # Key bindings
        self.root.bind('<Escape>', lambda e: self.stop())
        self.root.bind('<space>', lambda e: self.toggle_pause())
        self.root.bind('<q>', lambda e: self.stop())
        self.root.bind('<Q>', lambda e: self.stop())
        self.root.bind('<Left>', lambda e: self._adjust_speed(-20))
        self.root.bind('<Right>', lambda e: self._adjust_speed(20))

        # Create initial UI elements
        self._create_ui_elements()

    def _draw_background(self):
        """Draw a cinematic gradient background"""
        # Create gradient from dark blue to black
        for i in range(0, self.screen_height, 4):
            ratio = i / self.screen_height
            # Dark blue to darker blue gradient
            r = int(5 + ratio * 5)
            g = int(5 + ratio * 10)
            b = int(15 + ratio * 20)
            color = f'#{r:02x}{g:02x}{b:02x}'
            self.canvas.create_rectangle(
                0, i, self.screen_width, i + 4,
                fill=color, outline=color
            )

        # Add some ambient "stars" / particles
        for _ in range(100):
            x = random.randint(0, self.screen_width)
            y = random.randint(0, self.screen_height)
            size = random.randint(1, 3)
            brightness = random.randint(30, 80)
            color = f'#{brightness:02x}{brightness:02x}{brightness + 20:02x}'
            self.canvas.create_oval(
                x, y, x + size, y + size,
                fill=color, outline=''
            )

    def _create_ui_elements(self):
        """Create static UI elements"""
        # Title at top
        self.title_id = self.canvas.create_text(
            self.screen_width // 2, 50,
            text="THE HISTORY OF CHESS & ARTIFICIAL INTELLIGENCE",
            font=tkfont.Font(family="Segoe UI", size=28, weight="bold"),
            fill='#e0e0e0',
            anchor='center'
        )

        # Subtitle
        self.subtitle_id = self.canvas.create_text(
            self.screen_width // 2, 90,
            text="A Documentary Journey Through Time",
            font=tkfont.Font(family="Segoe UI", size=16, slant="italic"),
            fill='#888888',
            anchor='center'
        )

        # Current topic display (bottom left)
        self.topic_id = self.canvas.create_text(
            30, self.screen_height - 60,
            text="",
            font=tkfont.Font(family="Segoe UI", size=14),
            fill='#666666',
            anchor='w'
        )

        # Speed indicator (bottom right)
        self.speed_id = self.canvas.create_text(
            self.screen_width - 30, self.screen_height - 30,
            text=f"Speed: {self.speed}",
            font=tkfont.Font(family="Segoe UI", size=12),
            fill='#444444',
            anchor='e'
        )

        # Instructions
        self.canvas.create_text(
            self.screen_width - 30, self.screen_height - 60,
            text="[ESC] Exit  [SPACE] Pause  [←→] Speed",
            font=tkfont.Font(family="Segoe UI", size=10),
            fill='#333333',
            anchor='e'
        )

    def _adjust_speed(self, delta: int):
        """Adjust presentation speed"""
        self.speed = max(1, min(200, self.speed + delta))
        self.canvas.itemconfig(self.speed_id, text=f"Speed: {self.speed}")

    def toggle_pause(self):
        """Toggle pause state"""
        self.paused = not self.paused

    def add_floating_image(self, image_path: str, start_pos: str = "random"):
        """Add a floating image element"""
        try:
            img = Image.open(image_path)

            # Random size
            scale = random.uniform(0.3, 0.8)
            max_dim = min(400, self.screen_width // 3)
            img.thumbnail((int(max_dim * scale), int(max_dim * scale)), Image.Resampling.LANCZOS)

            # Add slight vignette/glow effect
            img = img.convert('RGBA')

            photo = ImageTk.PhotoImage(img)
            self.background_images.append(photo)  # Keep reference

            # Starting position
            if start_pos == "random":
                x = random.randint(100, self.screen_width - 100)
                y = random.randint(150, self.screen_height - 150)
            elif start_pos == "left":
                x = -100
                y = random.randint(150, self.screen_height - 150)
            elif start_pos == "right":
                x = self.screen_width + 100
                y = random.randint(150, self.screen_height - 150)
            else:
                x = self.screen_width // 2
                y = self.screen_height // 2

            element = FloatingElement(
                x=x, y=y,
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(-0.3, 0.3),
                scale=scale,
                alpha=0.0,  # Fade in
                rotation=0,
                rotation_speed=random.uniform(-0.5, 0.5),
                image=photo,
                element_type="image",
                lifetime=random.uniform(20, 40)
            )

            # Create on canvas
            element.canvas_id = self.canvas.create_image(
                x, y, image=photo, anchor='center'
            )

            self.floating_elements.append(element)

        except Exception as e:
            print(f"Error adding floating image: {e}")

    def add_floating_text(self, text: str, style: str = "quote"):
        """Add floating text element"""
        x = random.randint(100, self.screen_width - 300)
        y = random.randint(200, self.screen_height - 200)

        if style == "quote":
            font_size = random.randint(16, 24)
            color = '#c0c0c0'
        elif style == "fact":
            font_size = random.randint(14, 18)
            color = '#80a0c0'
        else:
            font_size = 16
            color = '#a0a0a0'

        element = FloatingElement(
            x=x, y=y,
            vx=random.uniform(-0.2, 0.2),
            vy=random.uniform(-0.1, 0.1),
            scale=1.0,
            alpha=0.0,
            rotation=0,
            rotation_speed=0,
            text=text,
            element_type="text",
            lifetime=random.uniform(15, 25)
        )

        element.canvas_id = self.canvas.create_text(
            x, y,
            text=text,
            font=tkfont.Font(family="Segoe UI", size=font_size),
            fill=color,
            anchor='center',
            width=min(500, self.screen_width - 200)
        )

        self.floating_elements.append(element)

    def add_scrolling_text(self, text: str, y_pos: float = None, direction: str = "left"):
        """Add horizontally scrolling text"""
        if y_pos is None:
            y_pos = random.randint(int(self.screen_height * 0.3), int(self.screen_height * 0.7))

        if direction == "left":
            x = self.screen_width + 100
            speed = -random.uniform(1, 3)
        else:
            x = -500
            speed = random.uniform(1, 3)

        scroll = ScrollingText(
            text=text,
            x=x,
            y=y_pos,
            speed=speed,
            font_size=random.randint(14, 20),
            color='#70a0d0',
            direction=direction
        )

        scroll.canvas_id = self.canvas.create_text(
            x, y_pos,
            text=text,
            font=tkfont.Font(family="Segoe UI", size=scroll.font_size),
            fill=scroll.color,
            anchor='w' if direction == "left" else 'e'
        )

        self.scrolling_texts.append(scroll)

    def _update_animations(self):
        """Update all animated elements"""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time

        speed_mult = self.speed / 100.0

        # Update floating elements
        elements_to_remove = []
        for elem in self.floating_elements:
            elem.age += dt
            if elem.age > elem.lifetime:
                elements_to_remove.append(elem)
                continue

            # Fade in/out
            if elem.age < 2:
                elem.alpha = elem.age / 2
            elif elem.age > elem.lifetime - 2:
                elem.alpha = (elem.lifetime - elem.age) / 2
            else:
                elem.alpha = 1.0

            # Update position
            elem.x += elem.vx * speed_mult
            elem.y += elem.vy * speed_mult

            # Bounce off edges
            if elem.x < 50 or elem.x > self.screen_width - 50:
                elem.vx *= -1
            if elem.y < 120 or elem.y > self.screen_height - 80:
                elem.vy *= -1

            # Update canvas
            self.canvas.coords(elem.canvas_id, elem.x, elem.y)

        # Remove dead elements
        for elem in elements_to_remove:
            self.canvas.delete(elem.canvas_id)
            self.floating_elements.remove(elem)

        # Update scrolling texts
        scrolls_to_remove = []
        for scroll in self.scrolling_texts:
            scroll.x += scroll.speed * speed_mult

            # Remove if off screen
            if scroll.direction == "left" and scroll.x < -600:
                scrolls_to_remove.append(scroll)
            elif scroll.direction == "right" and scroll.x > self.screen_width + 600:
                scrolls_to_remove.append(scroll)
            else:
                self.canvas.coords(scroll.canvas_id, scroll.x, scroll.y)

        for scroll in scrolls_to_remove:
            self.canvas.delete(scroll.canvas_id)
            self.scrolling_texts.remove(scroll)

    def _animation_loop(self):
        """Main animation loop"""
        last_quote_time = 0
        last_fact_time = 0
        last_image_time = 0

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            current_time = time.time()

            # Add periodic content
            if current_time - last_quote_time > 8:
                quote = random.choice(self.chess_quotes)
                self.root.after(0, lambda q=quote: self.add_floating_text(q, "quote"))
                last_quote_time = current_time

            if current_time - last_fact_time > 6:
                fact = random.choice(self.historical_facts)
                self.root.after(0, lambda f=fact: self.add_scrolling_text(f))
                last_fact_time = current_time

            if current_time - last_image_time > 5:
                images = self._get_random_images(1)
                for img_path in images:
                    self.root.after(0, lambda p=img_path: self.add_floating_image(p))
                last_image_time = current_time

            # Update animations
            self.root.after(0, self._update_animations)

            time.sleep(self.frame_time)

    def _get_random_images(self, count: int = 1) -> List[str]:
        """Get random images from the data folder"""
        images = []
        if IMAGES_DIR.exists():
            all_images = list(IMAGES_DIR.rglob("*.jpg")) + \
                        list(IMAGES_DIR.rglob("*.png")) + \
                        list(IMAGES_DIR.rglob("*.webp"))
            if all_images:
                images = [str(p) for p in random.sample(all_images, min(count, len(all_images)))]
        return images

    def _content_loop(self):
        """Background content fetching loop"""
        while self.running:
            if self.on_need_content:
                self.on_need_content()
            time.sleep(30)  # Fetch new content every 30 seconds

    def update_topic(self, topic: str):
        """Update the current topic display"""
        self.current_topic = topic
        if self.topic_id:
            self.canvas.itemconfig(self.topic_id, text=f"Current: {topic}")

    def start(self):
        """Start the cinematic overlay"""
        print("[Cinematic] Starting overlay...")
        self.setup_ui()
        self.running = True

        # Start animation thread
        self.animation_thread = threading.Thread(target=self._animation_loop, daemon=True)
        self.animation_thread.start()

        # Start content thread
        self.content_thread = threading.Thread(target=self._content_loop, daemon=True)
        self.content_thread.start()

        # Add some initial content
        self.root.after(1000, lambda: self.add_floating_text(
            "From ancient India to modern AI...", "quote"))
        self.root.after(2000, lambda: self.add_scrolling_text(
            "CHESS: The Game of Kings - A 1500 Year Journey"))

        # Main loop
        self.root.mainloop()

    def stop(self):
        """Stop the overlay"""
        print("[Cinematic] Stopping...")
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None


# Test
if __name__ == "__main__":
    overlay = CinematicOverlay(None)
    overlay.start()
