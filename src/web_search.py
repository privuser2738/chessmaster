"""
Web Search and Content Fetching Module
Searches the web for chess content and downloads resources
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

from config import (
    USER_AGENT, CHESS_TOPICS, CHESS_DOMAINS,
    CONTENT_DIR, IMAGES_DIR, CACHE_DIR,
    MAX_CONTENT_LENGTH, MIN_CONTENT_LENGTH, MAX_IMAGES_PER_TOPIC
)


@dataclass
class SearchResult:
    """Represents a search result"""
    title: str
    url: str
    snippet: str
    domain: str
    timestamp: str


@dataclass
class ContentItem:
    """Represents fetched content"""
    id: str
    title: str
    url: str
    text_content: str
    excerpts: List[str]
    images: List[str]
    topic: str
    source_type: str  # 'html', 'pdf', 'text'
    timestamp: str
    local_images: List[str]


class WebSearcher:
    """Handles web searching and content fetching for chess topics"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.searched_urls = set()
        self.topic_index = 0
        self._load_cache()

    def _load_cache(self):
        """Load previously searched URLs from cache"""
        cache_file = CACHE_DIR / "searched_urls.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.searched_urls = set(json.load(f))
            except:
                self.searched_urls = set()

    def _save_cache(self):
        """Save searched URLs to cache"""
        cache_file = CACHE_DIR / "searched_urls.json"
        with open(cache_file, 'w') as f:
            json.dump(list(self.searched_urls)[-1000:], f)  # Keep last 1000

    def get_next_topic(self) -> str:
        """Get the next chess topic to search, cycling through all topics"""
        topic = CHESS_TOPICS[self.topic_index % len(CHESS_TOPICS)]
        self.topic_index += 1
        # Add variation to searches
        variations = [
            topic,
            f"{topic} tutorial",
            f"{topic} guide",
            f"{topic} lesson",
            f"{topic} examples",
            f"learn {topic}",
            f"{topic} explained"
        ]
        return random.choice(variations)

    def search_web(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search the web for chess content"""
        results = []

        if HAS_DDGS:
            try:
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(
                        query,
                        max_results=max_results,
                        safesearch='moderate'
                    ))

                    for r in search_results:
                        url = r.get('href', r.get('link', ''))
                        if url and url not in self.searched_urls:
                            parsed = urlparse(url)
                            results.append(SearchResult(
                                title=r.get('title', 'Chess Content'),
                                url=url,
                                snippet=r.get('body', r.get('snippet', '')),
                                domain=parsed.netloc,
                                timestamp=datetime.now().isoformat()
                            ))
            except Exception as e:
                print(f"DuckDuckGo search error: {e}")

        # Fallback: Search specific chess sites directly
        if not results:
            results = self._search_chess_sites(query)

        return results

    def _search_chess_sites(self, query: str) -> List[SearchResult]:
        """Fallback search using direct site queries"""
        results = []
        search_urls = [
            f"https://www.chess.com/article/search?q={query.replace(' ', '+')}",
            f"https://lichess.org/search?q={query.replace(' ', '+')}",
        ]

        for base_url in search_urls[:2]:  # Limit to avoid rate limiting
            try:
                parsed = urlparse(base_url)
                results.append(SearchResult(
                    title=f"Chess content: {query}",
                    url=base_url,
                    snippet=f"Search results for: {query}",
                    domain=parsed.netloc,
                    timestamp=datetime.now().isoformat()
                ))
            except:
                pass

        return results

    def search_images(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for chess-related images"""
        images = []

        if HAS_DDGS:
            try:
                with DDGS() as ddgs:
                    image_results = list(ddgs.images(
                        f"{query} chess diagram",
                        max_results=max_results,
                        safesearch='moderate'
                    ))

                    for img in image_results:
                        images.append({
                            'url': img.get('image', ''),
                            'thumbnail': img.get('thumbnail', ''),
                            'title': img.get('title', ''),
                            'source': img.get('source', '')
                        })
            except Exception as e:
                print(f"Image search error: {e}")

        return images

    def fetch_content(self, url: str, topic: str) -> Optional[ContentItem]:
        """Fetch and parse content from a URL"""
        if url in self.searched_urls:
            return None

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()

            self.searched_urls.add(url)
            self._save_cache()

            if 'application/pdf' in content_type:
                return self._process_pdf(response, url, topic)
            elif 'text/plain' in content_type:
                return self._process_text(response, url, topic)
            else:
                return self._process_html(response, url, topic)

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _process_html(self, response, url: str, topic: str) -> Optional[ContentItem]:
        """Process HTML content"""
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe']):
            tag.decompose()

        # Get title
        title = soup.title.string if soup.title else topic.title()
        title = title[:200] if title else "Chess Content"

        # Extract main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|article|post|entry'))
        if not main_content:
            main_content = soup.body or soup

        # Get text content
        text_content = main_content.get_text(separator='\n', strip=True)
        text_content = re.sub(r'\n{3,}', '\n\n', text_content)  # Reduce multiple newlines

        if len(text_content) < MIN_CONTENT_LENGTH:
            return None

        text_content = text_content[:MAX_CONTENT_LENGTH]

        # Extract meaningful excerpts (paragraphs)
        excerpts = []
        for p in main_content.find_all(['p', 'li', 'h2', 'h3']):
            text = p.get_text(strip=True)
            if len(text) > 50 and len(text) < 1000:
                # Filter for chess-related content
                chess_keywords = ['chess', 'piece', 'pawn', 'knight', 'bishop', 'rook', 'queen', 'king',
                                'move', 'checkmate', 'opening', 'endgame', 'tactic', 'strategy',
                                'position', 'attack', 'defense', 'castle', 'gambit', 'sacrifice']
                if any(kw in text.lower() for kw in chess_keywords) or len(excerpts) < 3:
                    excerpts.append(text)

        if not excerpts:
            # Fallback: split content into chunks
            sentences = text_content.split('.')
            excerpts = ['. '.join(sentences[i:i+3]) + '.' for i in range(0, min(9, len(sentences)), 3)]

        # Extract images
        images = []
        for img in main_content.find_all('img', src=True)[:MAX_IMAGES_PER_TOPIC]:
            src = img['src']
            if not src.startswith('data:'):
                full_url = urljoin(url, src)
                if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    images.append(full_url)

        # Download images locally
        local_images = self._download_images(images, topic)

        content_id = hashlib.md5(url.encode()).hexdigest()[:12]

        return ContentItem(
            id=content_id,
            title=title,
            url=url,
            text_content=text_content,
            excerpts=excerpts[:10],
            images=images,
            topic=topic,
            source_type='html',
            timestamp=datetime.now().isoformat(),
            local_images=local_images
        )

    def _process_pdf(self, response, url: str, topic: str) -> Optional[ContentItem]:
        """Process PDF content (save for later extraction)"""
        content_id = hashlib.md5(url.encode()).hexdigest()[:12]
        from config import PDFS_DIR

        # Save PDF
        pdf_path = PDFS_DIR / f"{content_id}.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(response.content)

        # Basic text extraction attempt
        text_content = f"PDF Document about {topic}"
        try:
            import PyPDF2
            pdf_path_str = str(pdf_path)
            with open(pdf_path_str, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []
                for page in reader.pages[:10]:  # First 10 pages
                    text_parts.append(page.extract_text() or '')
                text_content = '\n'.join(text_parts)[:MAX_CONTENT_LENGTH]
        except:
            pass

        return ContentItem(
            id=content_id,
            title=f"Chess PDF: {topic}",
            url=url,
            text_content=text_content,
            excerpts=[text_content[:500]] if text_content else [],
            images=[],
            topic=topic,
            source_type='pdf',
            timestamp=datetime.now().isoformat(),
            local_images=[]
        )

    def _process_text(self, response, url: str, topic: str) -> Optional[ContentItem]:
        """Process plain text content"""
        text_content = response.text[:MAX_CONTENT_LENGTH]

        if len(text_content) < MIN_CONTENT_LENGTH:
            return None

        content_id = hashlib.md5(url.encode()).hexdigest()[:12]

        # Split into excerpts
        paragraphs = text_content.split('\n\n')
        excerpts = [p.strip() for p in paragraphs if len(p.strip()) > 50][:10]

        return ContentItem(
            id=content_id,
            title=f"Chess Text: {topic}",
            url=url,
            text_content=text_content,
            excerpts=excerpts,
            images=[],
            topic=topic,
            source_type='text',
            timestamp=datetime.now().isoformat(),
            local_images=[]
        )

    def _download_images(self, image_urls: List[str], topic: str) -> List[str]:
        """Download images and return local paths"""
        local_paths = []
        topic_dir = IMAGES_DIR / topic.replace(' ', '_')[:30]
        topic_dir.mkdir(parents=True, exist_ok=True)

        for url in image_urls[:MAX_IMAGES_PER_TOPIC]:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Determine extension
                    content_type = response.headers.get('content-type', '')
                    ext = '.jpg'
                    if 'png' in content_type:
                        ext = '.png'
                    elif 'gif' in content_type:
                        ext = '.gif'
                    elif 'webp' in content_type:
                        ext = '.webp'

                    filename = hashlib.md5(url.encode()).hexdigest()[:10] + ext
                    filepath = topic_dir / filename

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    local_paths.append(str(filepath))
            except Exception as e:
                print(f"Error downloading image {url}: {e}")

            time.sleep(0.2)  # Rate limiting

        return local_paths

    def fetch_topic_content(self, topic: str = None) -> List[ContentItem]:
        """Search and fetch content for a chess topic"""
        if topic is None:
            topic = self.get_next_topic()

        print(f"Searching for: {topic}")
        results = self.search_web(topic)
        content_items = []

        for result in results[:5]:  # Limit to 5 pages per topic
            content = self.fetch_content(result.url, topic)
            if content:
                content_items.append(content)
                # Save content to disk
                self._save_content(content)
            time.sleep(0.5)  # Rate limiting

        # Also search for images
        images = self.search_images(topic)
        if images:
            self._download_search_images(images, topic)

        return content_items

    def _save_content(self, content: ContentItem):
        """Save content item to disk"""
        content_file = CONTENT_DIR / f"{content.id}.json"
        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(content), f, indent=2, ensure_ascii=False)

    def _download_search_images(self, images: List[Dict], topic: str):
        """Download images from search results"""
        topic_dir = IMAGES_DIR / topic.replace(' ', '_')[:30]
        topic_dir.mkdir(parents=True, exist_ok=True)

        for img in images[:5]:
            url = img.get('url') or img.get('thumbnail')
            if url:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        ext = '.jpg'
                        if 'png' in response.headers.get('content-type', ''):
                            ext = '.png'

                        filename = hashlib.md5(url.encode()).hexdigest()[:10] + ext
                        filepath = topic_dir / filename

                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                except:
                    pass
                time.sleep(0.3)


# Quick test
if __name__ == "__main__":
    searcher = WebSearcher()
    content = searcher.fetch_topic_content("chess opening principles")
    print(f"Fetched {len(content)} content items")
    for c in content:
        print(f"  - {c.title}: {len(c.excerpts)} excerpts, {len(c.local_images)} images")
