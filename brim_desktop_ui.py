import tkinter as tk
from typing import Tuple, Dict, Optional
import math
import os
from PIL import Image, ImageTk, ImageEnhance, ImageChops
import time

class DesktopBrio:
    """
    A native transparent desktop resident (sprite).
    Moves smoothly and reacts visually to Brio's internal state.
    Upgraded to 'Sentinel Orb' v2.6 (Stability & Settings).
    """
    def __init__(self, command_callback=None):
        self.root = tk.Tk()
        self.root.title("Brio Resident")
        self.command_callback = command_callback
        
        # 1. Window Configuration
        self.root.overrideredirect(True) 
        self.root.attributes("-topmost", True)
        
        # Magenta key for high-visibility transparency detection
        self.trans_color = "#ff00ff" 
        self.root.attributes("-transparentcolor", self.trans_color)
        self.root.config(bg=self.trans_color)
        
        # 2. Sprite Canvas
        self.size = 140
        self.scale = 1.0 
        self.bubble_width = 240
        self.canvas_height = 200 
        self.canvas = tk.Canvas(self.root, width=self.size + self.bubble_width, height=self.canvas_height, 
                               bg=self.trans_color, highlightthickness=0)
        self.canvas.pack()
        
        # 3. Animation & Position State
        self.pulse_phase = 0.0
        self.current_rgb = (0, 229, 255)
        self.intensity = 0.5
        self.bubble_timer = 0
        self._drag_data = {"x": 0, "y": 0}

        # 4. Visual Assets
        self.asset_path = "assets/orb_base.png"
        self.orb_image_raw = None
        self.orb_photo = None
        self.halo_id = None
        self._setup_visual_layers()
        
        # 5. UI Elements
        self.bubble = self.canvas.create_rectangle(self.size, 50, self.size + self.bubble_width - 5, self.size + 80,
                                                  fill="#121212", outline="#2a2a2a", state="hidden")
        self.bubble_text = self.canvas.create_text(self.size + 15, self.size//2 + 40, text="", 
                                                   fill="#00e5ff", font=("Consolas", 10), width=self.bubble_width-30,
                                                   anchor="w", state="hidden")
        
        self.input_field = tk.Entry(self.root, bg="#121212", fg="#00e5ff", insertbackground="#00e5ff",
                                    borderwidth=0, font=("Consolas", 11), justify="center")
        self.input_window = self.canvas.create_window(self.size//2, 25, window=self.input_field, 
                                                      width=self.size, state="hidden")
        
        self.input_field.bind("<Return>", self._on_input_submit)
        
        # 6. Context Menu
        self.menu = tk.Menu(self.root, tearoff=0, bg="#121212", fg="#00e5ff", activebackground="#00e5ff", activeforeground="#121212")
        self.menu.add_command(label="Brio Settings", command=lambda: self._trigger_cmd("settings"))
        self.menu.add_command(label="Ascension Progress", command=lambda: self._trigger_cmd("milestones"))
        self.menu.add_separator()
        self.menu.add_command(label="Terminate Brio", command=lambda: self._trigger_cmd("shutdown"))
        
        # 7. Bindings
        self.canvas.tag_bind(self.halo_id, "<Enter>", lambda e: self._show_input(True))
        self.root.bind("<Leave>", lambda e: self._handle_leave(e))
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)
        self.root.bind("<MouseWheel>", self._on_resize)
        self.root.bind("<Button-3>", self._show_menu) # Right Click
        
        # 8. Default Position (Top-Right)
        screen_w = self.root.winfo_screenwidth()
        self.x = screen_w - (self.size + self.bubble_width + 40)
        self.y = 40
        self.target_x, self.target_y = self.x, self.y
        self._update_geometry()

    def _trigger_cmd(self, cmd: str):
        if self.command_callback:
            self.command_callback(cmd)

    def _show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def _update_geometry(self):
        w = int((self.size + self.bubble_width) * self.scale)
        h = int(self.canvas_height * self.scale)
        self.root.geometry(f"{w}x{h}+{int(self.x)}+{int(self.y)}")

    def _setup_visual_layers(self):
        if os.path.exists(self.asset_path):
            img = Image.open(self.asset_path).convert("RGBA")
            self.orb_image_raw = img.resize((self.size, self.size), Image.Resampling.LANCZOS)
            self._render_procedural_orb()
        else:
            self.halo_id = self.canvas.create_oval(10, 40, self.size-10, self.size+20, fill="#00e5ff", outline="")

    def _render_procedural_orb(self):
        if not self.orb_image_raw: return
        cs = int(self.size * self.scale)
        scaled_base = self.orb_image_raw.resize((cs, cs), Image.Resampling.LANCZOS)
        
        # Pulse & Color
        pulse = 0.9 + 0.2 * abs(math.sin(self.pulse_phase))
        tint = Image.new("RGBA", scaled_base.size, self.current_rgb + (int(255 * 0.25),))
        blended = ImageChops.screen(scaled_base, tint)
        
        enhancer = ImageEnhance.Brightness(blended)
        final_img = enhancer.enhance(pulse * self.intensity * 2.2)
        
        self.orb_photo = ImageTk.PhotoImage(final_img)
        if self.halo_id:
            self.canvas.itemconfig(self.halo_id, image=self.orb_photo)
            self.canvas.coords(self.halo_id, cs//2, cs//2 + 40)
        else:
            self.halo_id = self.canvas.create_image(cs//2, cs//2 + 40, image=self.orb_photo)

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.x += dx
        self.y += dy
        self.target_x, self.target_y = self.x, self.y
        self._update_geometry()

    def _on_resize(self, event):
        increment = 0.1 if event.delta > 0 else -0.1
        self.scale = max(0.4, min(2.5, self.scale + increment))
        self._update_geometry()
        self._render_procedural_orb()

    def _show_input(self, visible: bool):
        state = "normal" if visible else "hidden"
        self.canvas.itemconfig(self.input_window, state=state)
        if visible:
            self.input_field.focus_set()

    def _handle_leave(self, event):
        if self.root.focus_get() != self.input_field:
            self._show_input(False)

    def _on_input_submit(self, event):
        cmd = self.input_field.get().strip()
        if cmd and self.command_callback:
            # Force immediate processing
            self.command_callback(cmd)
        self.input_field.delete(0, tk.END)
        self._show_input(False)
        self.root.focus_set()

    def _interpolate_movement(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) > 1 or abs(dy) > 1:
            self.x += dx * 0.1
            self.y += dy * 0.1
            self._update_geometry()

    def tick(self):
        # 1. Internal Logic
        self._interpolate_movement()
        self.pulse_phase += 0.08
        self._render_procedural_orb()
        
        if self.bubble_timer > 0:
            self.bubble_timer -= 1
            if self.bubble_timer == 0:
                self.canvas.itemconfig(self.bubble, state="hidden")
                self.canvas.itemconfig(self.bubble_text, state="hidden")
        
        # 2. Update TK
        try:
            self.root.update_idletasks()
            self.root.update()
        except:
            pass

    def set_target(self, x: int, y: int):
        self.target_x = x
        self.target_y = y

    def show_thought(self, text: str, duration_sec: int = 5):
        self.canvas.itemconfig(self.bubble, state="normal")
        self.canvas.itemconfig(self.bubble_text, state="normal", text=text)
        self.bubble_timer = duration_sec * 20 

    def update_visuals(self, color: str, intensity: float):
        try:
            h = color.lstrip('#')
            self.current_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except:
            self.current_rgb = (0, 229, 255)
        self.intensity = max(0.2, min(1.0, intensity))

    def run_loop(self):
        """Emergency blocking loop for dev testing, normally driven by main engine"""
        while True:
            self.tick()
            time.sleep(0.05)

if __name__ == "__main__":
    ui = DesktopBrio()
    ui.run_loop()
