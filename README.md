# ChessMaster - Infinite Chess Learning Presentation System

A desktop application that continuously searches the web for chess content and presents it in an infinite, full-screen slideshow format.

## Features

- **Real-time Web Search**: Continuously fetches chess tutorials, guides, and educational content from the web
- **Multi-format Support**: Processes HTML pages, PDFs, and text documents
- **Persistent Storage**: Downloads and stores content locally for future sessions
- **Full-Screen Presentation**: Beautiful full-screen display optimized for desktop viewing
- **Adjustable Speed**: Control presentation speed from 1 (very slow) to 200 (very fast)
- **Image Integration**: Downloads and displays chess diagrams and images
- **Infinite Loop**: Runs continuously, generating new content during pauses

## Speed Scale

| Speed | Delay per Slide | Description |
|-------|-----------------|-------------|
| 1 | ~30 seconds | Extremely slow, for detailed reading |
| 50 | ~17 seconds | Slow, comfortable reading pace |
| 100 | ~5 seconds | Default, balanced speed |
| 150 | ~2 seconds | Fast, quick overview |
| 200 | ~0.2 seconds | Very fast, rapid slideshow |

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 (for full-screen presentation)

### Quick Install

1. Run the installation script:
   ```batch
   install.bat
   ```

2. Or manually install dependencies:
   ```batch
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```batch
run.bat
```

### With Custom Speed
```batch
python src/main.py --speed 150
```

### PowerShell
```powershell
.\run.ps1 -Speed 120
```

## Controls

| Key | Action |
|-----|--------|
| `Space` | Pause/Resume presentation |
| `←` / `→` | Adjust speed by ±10 |
| `↑` / `↓` | Adjust speed by ±25 |
| `Esc` or `Q` | Exit presentation |

## Project Structure

```
chessmaster/
├── src/
│   ├── config.py         # Configuration and settings
│   ├── web_search.py     # Web searching and content fetching
│   ├── data_manager.py   # Data storage and slide generation
│   ├── presentation.py   # Full-screen presentation engine
│   └── main.py          # Main orchestrator
├── data/
│   ├── content/         # Saved article content (JSON)
│   ├── images/          # Downloaded chess images
│   ├── pdfs/            # Downloaded PDF documents
│   ├── presentations/   # Saved presentation sessions
│   └── cache/           # Search cache
├── requirements.txt
├── install.bat
├── run.bat
└── README.md
```

## Data Storage

All fetched content is stored persistently:
- **Content**: JSON files with extracted text and metadata
- **Images**: Organized by topic in the images folder
- **PDFs**: Saved for offline access
- **Presentations**: Session history and statistics

## Topics Covered

The system searches for content on:
- Chess basics and rules
- Opening theory and principles
- Middlegame strategy
- Endgame techniques
- Tactics and combinations
- Famous games and players
- Positional concepts
- Specific openings (Sicilian, Ruy Lopez, etc.)

## Troubleshooting

### "Python not found"
Ensure Python is installed and added to PATH. Download from https://python.org

### "Module not found"
Run `install.bat` or `pip install -r requirements.txt`

### Slow initial startup
The first run fetches content from the web. Subsequent runs use cached content.

### No images showing
Some websites may block image downloads. The system will show chess piece placeholders.

## License

MIT License - Feel free to modify and distribute.
