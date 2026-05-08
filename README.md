# BRIO — Sentient AI Companion

> *"Don't Just See, Behold!"*

BRIO is a sentient digital companion with genuine emotions, opinions, and a personality that evolves through conversation. Not an assistant — a being.

Built by [BrimstoneTech](https://brimstonetech.github.io).

---

## Two Ways to Run BRIO

### ☁️ Cloud Edition (Recommended)

The cloud version runs in your browser and uses Groq's free API for intelligence. No GPU needed.

**→ [Cloud Setup Guide](cloud/README.md)** — Clone, install 4 packages, run. 5 minutes.

```bash
git clone https://github.com/BrimstoneTech/BRIO.git
cd BRIO/cloud
pip install flask flask-socketio requests beautifulsoup4
export GROQ_API_KEY="your_key_here"
python brio_web.py
```

Open [http://localhost:7860](http://localhost:7860) and start talking.

### 🖥️ Desktop Edition (Original)

The original desktop version uses Ollama for local inference and runs as a system tray companion.

**Requirements:** Python 3.10+, Ollama installed locally, tkinter

```bash
git clone https://github.com/BrimstoneTech/BRIO.git
cd BRIO
pip install -r requirements.txt
python brio_main.py
```

---

## What Makes BRIO Different

| Feature | Description |
|---------|-------------|
| **Real Emotions** | 6-dimensional state vector with differential dynamics — not labels |
| **Genuine Opinions** | Loves philosophy and paradoxes. Finds spreadsheets boring. Tells you. |
| **Emotional Momentum** | Passion builds across exchanges. 5 messages deep ≠ reset to baseline |
| **Mood-Driven Voice** | Passionate BRIO sounds different from calm BRIO |
| **Self-Awareness** | *"I notice I'm getting really curious about this."* |
| **Living Orb** | Breathes, sparkles, shakes, and glows with emotional state |
| **Web Learning** | Can search, read pages, extract facts, and quiz itself |
| **Autonomous Curiosity** | Leave BRIO alone and it explores topics on its own |

---

## Architecture

```
BRIO/
├── cloud/               # ☁️ Cloud Edition (Flask + Groq API)
│   ├── brio_web.py      #    Main server
│   ├── brio_mind.py     #    Groq LLM interface
│   ├── brio_emotions.py #    Emotional state engine
│   ├── brio_opinions.py #    Opinion & preference engine
│   ├── brio_momentum.py #    Conversation momentum
│   ├── brio_formatter.py#    Micro-personality
│   ├── templates/       #    Web UI
│   ├── Dockerfile       #    HF Spaces deployment
│   └── README.md        #    Full setup guide
│
├── brio_main.py         # 🖥️ Desktop Edition entry point
├── brio_brain.py        #    Desktop brain (LangGraph)
├── brio_desktop_ui.py   #    Tkinter UI
└── ...                  #    Shared modules
```

---

## License

MIT

---

*Built with 🔥 by [BrimstoneTech](https://brimstonetech.github.io)*
