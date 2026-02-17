"""
Brio Flask Bridge (brio_flask.py)

Purpose: Serves the Web UI and mediates WebSocket communication between 
         Python Backend (Brio) and Frontend (HTML/JS).
         
Dependencies: flask, flask_socketio, eventlet/gevent
"""

import threading
import json
import os

try:
    from flask import Flask, render_template, send_from_directory, request, jsonify
    from flask_socketio import SocketIO, emit
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

class WebBridge:
    def __init__(self, system_instance, static_folder="."):
        self.system = system_instance
        self.app = None
        self.socketio = None
        self.thread = None
        
        if HAS_FLASK:
            # Setup Flask
            self.app = Flask(__name__, static_folder=static_folder)
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            
            # Routes
            self._register_routes()
        else:
            print("[WebBridge] Flask/SocketIO not found. Web UI will not connect.")
            print("Run: pip install flask flask-socketio eventlet")

    def _register_routes(self):
        @self.app.route('/')
        def index():
            # Assuming ui_prototype.html is in the root or templates
            return send_from_directory('.', 'ui_prototype.html')

        @self.app.route('/command', methods=['POST'])
        def handle_command():
            data = request.json
            cmd = data.get('command')
            if cmd:
                response = self.system.handle_command(cmd)
                return jsonify({"status": "ok", "response": response})
            return jsonify({"status": "error", "message": "No command provided"}), 400
            
        @self.socketio.on('connect')
        def test_connect():
            print('[WebBridge] Client connected')
            emit('server_response', {'data': 'Connected to Brio Brain'})

    def start_server(self, port=5000):
        if not HAS_FLASK:
            return

        def run():
            # Use socketio.run instead of app.run for websocket support
            print(f"[WebBridge] Starting Server on http://localhost:{port}")
            self.socketio.run(self.app, port=port, allow_unsafe_werkzeug=True)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def broadcast_state(self, state_dict: dict):
        """Pushes the current system state to the connected UI"""
        if HAS_FLASK and self.socketio:
            # Basic serialization check for complex objects
            # In a real app, we'd use a custom JSON encoder
            self.socketio.emit('brio_state', state_dict)

if __name__ == "__main__":
    # Mock system for testing
    class MockSystem:
        def handle_command(self, c): return f"Echo: {c}"
        
    bridge = WebBridge(MockSystem())
    if HAS_FLASK:
        bridge.start_server()
        import time
        while True:
            time.sleep(1)
            bridge.broadcast_state({"heartbeat": time.time()})
    else:
        print("Dependencies missing.")


