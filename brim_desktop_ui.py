
import tkinter as tk
from typing import Tuple, Dict
import math

class DesktopBrio:
    """
    A native transparent desktop resident (sprite).
    Moves smoothly and reacts visually to Brio's internal state.
    """
    def __init__(self, command_callback=None):
        self.root = tk.Tk()
        self.root.title("Brio Resident")
        self.command_callback = command_callback
        
        # 1. Window Configuration
        self.root.overrideredirect(True) # Frameless
        self.root.attributes("-topmost", True) # Always on top
        self.root.attributes("-transparentcolor", "black") # Black is transparent
        self.root.config(bg="black")
        
        # 2. Sprite Canvas
        self.size = 120
        self.bubble_width = 200
        self.canvas_height = 160 # Extra space for input box
        self.canvas = tk.Canvas(self.root, width=self.size + self.bubble_width, height=self.canvas_height, 
                               bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # Draw the "Halo" (Circular Sprite)
        self.halo = self.canvas.create_oval(10, 40, self.size-10, self.size+20, 
                                           fill="#00ffff", outline="")
        self.inner = self.canvas.create_oval(30, 60, self.size-30, self.size, 
                                            fill="#111111", outline="")
        
        # Draw the "Thought Bubble" (Hidden by default)
        self.bubble = self.canvas.create_rectangle(self.size, 40, self.size + self.bubble_width - 5, self.size + 20,
                                                  fill="#222222", outline="#555555", state="hidden")
        self.bubble_text = self.canvas.create_text(self.size + 10, self.size//2 + 30, text="", 
                                                   fill="white", font=("Arial", 10), width=self.bubble_width-20,
                                                   anchor="w", state="hidden")
        
        # 3. Input Widget (Shown on hover)
        self.input_frame = tk.Frame(self.root, bg="#333333", padx=2, pady=2)
        self.input_field = tk.Entry(self.input_frame, bg="#222222", fg="white", 
                                    insertbackground="white", borderwidth=0, font=("Arial", 9))
        self.input_field.pack(fill="x")
        self.input_field.bind("<Return>", self._on_input_submit)
        self.input_window = self.canvas.create_window(self.size//2, 20, window=self.input_frame, 
                                                      width=self.size+40, state="hidden")
        
        # Hover Bindings
        self.canvas.tag_bind(self.halo, "<Enter>", lambda e: self._show_input(True))
        self.canvas.tag_bind(self.inner, "<Enter>", lambda e: self._show_input(True))
        self.root.bind("<Leave>", lambda e: self._show_input(False))

        # 4. Position State
        self.x, self.y = 500, 500
        self.target_x, self.target_y = 500, 500
        self.root.geometry(f"{self.size + self.bubble_width}x{self.canvas_height}+{int(self.x)}+{int(self.y)}")
        
        # 5. Animation State
        self.pulse_phase = 0.0
        self.current_color = "#00ffff"
        self.bubble_timer = 0
        
    def set_target(self, x: int, y: int):
        """Set screen coordinates for Brio to move toward"""
        self.target_x = x - (self.size // 2)
        self.target_y = y - (self.size // 2)

    def show_thought(self, text: str, duration_sec: int = 5):
        """Display a visual thought bubble"""
        self.canvas.itemconfig(self.bubble, state="normal")
        self.canvas.itemconfig(self.bubble_text, state="normal", text=text)
        self.bubble_timer = duration_sec * 50 # assuming 20ms ticks

    def update_visuals(self, color: str, intensity: float):
        """Update the Halo color and pulse intensity"""
        self.current_color = color

    def _show_input(self, visible: bool):
        """Toggle input field visibility"""
        state = "normal" if visible else "hidden"
        self.canvas.itemconfig(self.input_window, state=state)
        if visible:
            self.input_field.focus_set()

    def _on_input_submit(self, event):
        """Submit command from input field"""
        cmd = self.input_field.get().strip()
        if cmd and self.command_callback:
            self.command_callback(cmd)
        self.input_field.delete(0, tk.END)
        self._show_input(False)

    def _interpolate_movement(self):
        """Smoothly move towards target"""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        
        speed = 0.1
        if abs(dx) > 1 or abs(dy) > 1:
            self.x += dx * speed
            self.y += dy * speed
            self.root.geometry(f"{self.size + self.bubble_width}x{self.canvas_height}+{int(self.x)}+{int(self.y)}")

    def _animate_pulse(self):
        """Animate the halo scale/glow and bubble duration"""
        self.pulse_phase += 0.1
        self.canvas.itemconfig(self.halo, fill=self.current_color)
        
        if self.bubble_timer > 0:
            self.bubble_timer -= 1
            if self.bubble_timer == 0:
                self.canvas.itemconfig(self.bubble, state="hidden")
                self.canvas.itemconfig(self.bubble_text, state="hidden")

    def tick(self):
        """Main UI update cycle"""
        self._interpolate_movement()
        self._animate_pulse()
        self.root.update()

    def run_loop(self):
        """Blocking loop if needed, but we usually call tick() from main engine"""
        while True:
            self.tick()
            self.root.after(20)

if __name__ == "__main__":
    # Test Standalone
    brio_ui = DesktopBrio()
    brio_ui.set_target(800, 400)
    
    def demo_loop():
        brio_ui.tick()
        brio_ui.root.after(20, demo_loop)
    
    brio_ui.root.after(20, demo_loop)
    brio_ui.root.mainloop()
