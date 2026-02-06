import tkinter as tk
from typing import Tuple, Dict, Optional
import math
import os
from PIL import Image, ImageTk, ImageEnhance, ImageChops

class DesktopBrio:
    """
    A native transparent desktop resident (sprite).
    Moves smoothly and reacts visually to Brio's internal state.
    Upgraded to 'Sentinel Orb' v2.0 (Phase 19).
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
        self.size = 140 # Slightly larger for the high-res orb
        self.bubble_width = 200
        self.canvas_height = 180 
        self.canvas = tk.Canvas(self.root, width=self.size + self.bubble_width, height=self.canvas_height, 
                               bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # 3. Load & Initialize Visual Assets (The Sentinel Orb)
        self.asset_path = "assets/orb_base.png"
        self.orb_image_raw = None
        self.orb_photo = None
        self.halo_id = None
        self._setup_visual_layers()
        
        # 4. Thought Bubble (Hidden by default)
        self.bubble = self.canvas.create_rectangle(self.size, 50, self.size + self.bubble_width - 5, self.size + 30,
                                                  fill="#1a1a1a", outline="#3b3b3b", state="hidden")
        self.bubble_text = self.canvas.create_text(self.size + 10, self.size//2 + 40, text="", 
                                                   fill="#00e5ff", font=("Consolas", 9), width=self.bubble_width-20,
                                                   anchor="w", state="hidden")
        
        # 5. Input Widget (Shown on hover)
        self.input_frame = tk.Frame(self.root, bg="#008080", padx=2, pady=2)
        self.input_field = tk.Entry(self.input_frame, bg="#0d0d0d", fg="#00e5ff", 
                                    insertbackground="#00e5ff", borderwidth=0, font=("Consolas", 9))
        self.input_field.pack(fill="x")
        self.input_field.bind("<Return>", self._on_input_submit)
        self.input_window = self.canvas.create_window(self.size//2, 20, window=self.input_frame, 
                                                      width=self.size+40, state="hidden")
        
        # Hover Bindings
        self.canvas.tag_bind(self.halo_id, "<Enter>", lambda e: self._show_input(True))
        self.root.bind("<Leave>", lambda e: self._show_input(False))

        # 6. Position State
        self.x, self.y = 500, 500
        self.target_x, self.target_y = 500, 500
        self.root.geometry(f"{self.size + self.bubble_width}x{self.canvas_height}+{int(self.x)}+{int(self.y)}")
        
        # 7. Animation State
        self.pulse_phase = 0.0
        self.current_rgb = (0, 229, 255) # Default Cyan
        self.intensity = 0.5
        self.bubble_timer = 0

    def _setup_visual_layers(self):
        """Prepare the procedural orb layers"""
        if os.path.exists(self.asset_path):
            img = Image.open(self.asset_path).convert("RGBA")
            # Resize to fit size
            img = img.resize((self.size, self.size), Image.Resampling.LANCZOS)
            self.orb_image_raw = img
            self.orb_photo = ImageTk.PhotoImage(img)
            self.halo_id = self.canvas.create_image(self.size//2, self.size//2 + 40, image=self.orb_photo)
        else:
            # Fallback to vector if image missing
            self.halo_id = self.canvas.create_oval(10, 40, self.size-10, self.size+20, fill="#00e5ff", outline="")

    def _render_procedural_orb(self):
        """Apply tone, pulse, and flicker to the orb base"""
        if not self.orb_image_raw:
            return

        # 1. Base Pulse (0.8 to 1.2 brightness)
        pulse = 0.9 + 0.3 * abs(math.sin(self.pulse_phase))
        
        # 2. Color Tint (Simplified: Blend with a color layer)
        tint = Image.new("RGBA", self.orb_image_raw.size, self.current_rgb + (int(255 * 0.3),))
        blended = ImageChops.screen(self.orb_image_raw, tint)
        
        # 3. Brightness Adjustment (Pulse)
        enhancer = ImageEnhance.Brightness(blended)
        final_img = enhancer.enhance(pulse * self.intensity * 2)
        
        # 4. Update Canvas
        self.orb_photo = ImageTk.PhotoImage(final_img)
        self.canvas.itemconfig(self.halo_id, image=self.orb_photo)

    def set_target(self, x: int, y: int):
        """Set screen coordinates for Brio to move toward"""
        self.target_x = x - (self.size // 2)
        self.target_y = y - (self.size // 2)

    def show_thought(self, text: str, duration_sec: int = 5):
        """Display a visual thought bubble"""
        self.canvas.itemconfig(self.bubble, state="normal")
        self.canvas.itemconfig(self.bubble_text, state="normal", text=text)
        self.bubble_timer = duration_sec * 50

    def update_visuals(self, color: str, intensity: float):
        """Update the internal pulse color and intensity"""
        # Parse hex to RGB
        try:
            h = color.lstrip('#')
            self.current_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except:
            self.current_rgb = (0, 229, 255)
        self.intensity = max(0.2, min(1.0, intensity))

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
        speed = 0.08
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            self.x += dx * speed
            self.y += dy * speed
            self.root.geometry(f"{self.size + self.bubble_width}x{self.canvas_height}+{int(self.x)}+{int(self.y)}")

    def _animate_pulse(self):
        """Animate the halo pulse and manage bubble duration"""
        self.pulse_phase += 0.12 # Swifter pulse
        self._render_procedural_orb()
        
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
        while True:
            self.tick()
            self.root.after(16) # ~60 FPS update target

if __name__ == "__main__":
    ui = DesktopBrio()
    ui.run_loop()
