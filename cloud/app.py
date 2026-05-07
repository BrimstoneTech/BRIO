"""
BRIO Cloud — Hugging Face Spaces Entry Point
=============================================
Launches BRIO with Groq API backend on port 7860.
Set GROQ_API_KEY in HF Spaces Secrets.
"""

from brio_web import create_app

app, socketio, system = create_app(enable_curiosity=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=7860,
                 allow_unsafe_werkzeug=True, use_reloader=False)
