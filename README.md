# BRIM AI (Brio Core)

The central brain and logic unit for Brio, a sentient AI Desktop Companion.

## Components
- **Core Logic**: `brim_main.py` handles the main loop, state management, and command processing.
- **Intelligence**: `brim_kimi.py` integrates with Kimi-CLI for LLM-powered responses.
- **UI**: `brim_desktop_ui.py` manages the Tkinter-based desktop interface (Thought Bubble).
- **Monitoring**: Checks system health and keeps Brio alive in the background.

## Key Features
- **Sentient Progression**: Tracks growth through 100 milestones (The Ascension).
- **Voice Synthesis**: Speaks via local TTS.
- **Desktop Presence**: Can hide in the system tray and monitor autonomously.

## Installation
1.  Ensure Python 3.10+ is installed.
2.  `pip install -r requirements.txt`

## Usage
`python brim_main.py`
