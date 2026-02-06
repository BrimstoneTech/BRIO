import tkinter as tk
from typing import Tuple, Dict, Optional
import math
import os
from PIL import Image, ImageTk, ImageEnhance, ImageChops
import time
import pystray
from pystray import MenuItem as item
import threading

class DesktopBrio:
    """
    A native transparent desktop resident (sprite).
    Moves smoothly and reacts visually to Brio's internal state.
    Upgraded to 'Sentinel Orb' v2.7 (Zero-Box Transparency & Better Interaction).
    """
    def __init__(self, command_callback=None):
        self.root = tk.Tk()
        self.root.title("Brio Resident")
        self.command_callback = command_callback
        
        # 1. Window Configuration
        self.root.overrideredirect(True) 
        self.root.attributes("-topmost", True)
        
        # Transparent black-key for robust keying on Windows
        self.trans_color = "#000101" 
        self.root.config(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)
        
        # 2. Sprite Canvas
        self.size = 140
        self.scale = 1.0 
        self.bubble_width = 240
        self.canvas_height = 200 
        self.canvas = tk.Canvas(self.root, width=self.size + self.bubble_width, height=self.canvas_height, 
                               bg=self.trans_color, highlightthickness=0, bd=0)
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
        
        # 5. UI Elements: Thought Bubble
        self.bubble = self.canvas.create_rectangle(self.size, 40, self.size + self.bubble_width - 10, 140,
                                                  fill="#121212", outline="#2a2a2a", state="hidden")
        self.bubble_text = self.canvas.create_text(self.size + 15, 90, text="", 
                                                   fill="#00e5ff", font=("Consolas", 10), width=self.bubble_width-40,
                                                   anchor="w", state="hidden")
        
        # 6. Input Widget (Hover Prompt)
        self.input_field = tk.Entry(self.root, bg="#1a1a1a", fg="#00e5ff", insertbackground="#00e5ff",
                                    borderwidth=0, font=("Consolas", 12), justify="center")
        self.input_window = self.canvas.create_window(self.size//2, 25, window=self.input_field, 
                                                      width=self.size, state="hidden")
        
        self.input_field.bind("<Return>", self._on_input_submit)
        
        # 7. Context Menu
        self.menu = tk.Menu(self.root, tearoff=0, bg="#121212", fg="#00e5ff", activebackground="#00e5ff", activeforeground="#121212")
        self.menu.add_command(label="Brio Analytics", command=lambda: self._trigger_cmd("settings"))
        self.menu.add_command(label="Ascension Milestones", command=lambda: self._trigger_cmd("milestones"))
        self.menu.add_separator()
        self.menu.add_command(label="Hide to Tray", command=self._hide_brio)
        self.menu.add_command(label="Sleep / Power Off", command=lambda: self._trigger_cmd("shutdown"))
        
        # 8. Bindings
        self.canvas.tag_bind(self.halo_id, "<Enter>", lambda e: self._show_input(True))
        self.root.bind("<Leave>", lambda e: self._handle_leave(e))
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)
        self.root.bind("<MouseWheel>", self._on_resize)
        self.root.bind("<Button-3>", self._show_menu)
        
        # 9. Initial Position
        sw = self.root.winfo_screenwidth()
        self.x = sw - (self.size + self.bubble_width + 50)
        self.y = 50
        self.target_x, self.target_y = self.x, self.y
        self._update_geometry()

        # 10. System Tray Setup
        self.tray_icon = None
        self._setup_tray()

    def _setup_tray(self):
        """Initializes the system tray icon and menu"""
        if os.path.exists(self.asset_path):
            image = Image.open(self.asset_path)
        else:
            image = Image.new('RGB', (64, 64), (0, 229, 255))
            
        menu = (
            item('Restore Brio', self._show_brio, default=True),
            item('Background Hub', lambda: self._trigger_cmd("settings")),
            item('Exit Brio Entirely', self._on_exit_entirely)
        )
        self.tray_icon = pystray.Icon("Brio", image, "Brio Resident", menu)
        # Run tray in a separate thread to not block Tkinter
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _show_brio(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def _hide_brio(self):
        self.root.withdraw()

    def _on_exit_entirely(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self._trigger_cmd("shutdown_force")

    def _trigger_cmd(self, cmd: str):
        if self.command_callback: self.command_callback(cmd)

    def _show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def _update_geometry(self):
        w = int((self.size + self.bubble_width) * self.scale)
        h = int(self.canvas_height * self.scale)
        self.root.geometry(f"{w}x{h}+{int(self.x)}+{int(self.y)}")
        # Re-apply transparency key after geometry change (safety for some Windows versions)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

    def _setup_visual_layers(self):
        if os.path.exists(self.asset_path):
            img = Image.open(self.asset_path).convert("RGBA")
            self.orb_image_raw = img.resize((self.size, self.size), Image.Resampling.LANCZOS)
            self._render_procedural_orb()
        else:
            self.halo_id = self.canvas.create_oval(10, 40, self.size-10, self.size+150, fill="#00e5ff", outline="")

    def _render_procedural_orb(self):
        if not self.orb_image_raw: return
        cs = int(self.size * self.scale)
        scaled_base = self.orb_image_raw.resize((cs, cs), Image.Resampling.LANCZOS)
        
        pulse = 0.9 + 0.2 * abs(math.sin(self.pulse_phase))
        tint = Image.new("RGBA", scaled_base.size, self.current_rgb + (int(255 * 0.25),))
        blended = ImageChops.screen(scaled_base, tint)
        
        enhancer = ImageEnhance.Brightness(blended)
        final_img = enhancer.enhance(pulse * self.intensity * 2.5)
        
        self.orb_photo = ImageTk.PhotoImage(final_img)
        off_y = 50 * self.scale
        if self.halo_id:
            self.canvas.itemconfig(self.halo_id, image=self.orb_photo)
            self.canvas.coords(self.halo_id, cs//2, cs//2 + off_y)
        else:
            self.halo_id = self.canvas.create_image(cs//2, cs//2 + off_y, image=self.orb_photo)

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
        inc = 0.1 if event.delta > 0 else -0.1
        self.scale = max(0.4, min(2.5, self.scale + inc))
        self._update_geometry()
        self._render_procedural_orb()

    def _show_input(self, visible: bool):
        state = "normal" if visible else "hidden"
        self.canvas.itemconfig(self.input_window, state=state)
        if visible: self.input_field.focus_set()

    def _handle_leave(self, event):
        if self.root.focus_get() != self.input_field: self._show_input(False)

    def _on_input_submit(self, event):
        cmd = self.input_field.get().strip()
        if cmd and self.command_callback: self.command_callback(cmd)
        self.input_field.delete(0, tk.END)
        self._show_input(False)
        self.root.focus_set()

    def _interpolate_movement(self):
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if abs(dx) > 1 or abs(dy) > 1:
            self.x += dx * 0.12
            self.y += dy * 0.12
            self._update_geometry()

    def tick(self):
        self._interpolate_movement()
        self.pulse_phase += 0.08
        self._render_procedural_orb()
        
        if self.bubble_timer > 0:
            self.bubble_timer -= 1
            if self.bubble_timer == 0:
                self.canvas.itemconfig(self.bubble, state="hidden")
                self.canvas.itemconfig(self.bubble_text, state="hidden")
        
        try:
            self.root.update_idletasks()
            self.root.update()
        except: pass

    def set_target(self, x: int, y: int):
        self.target_x = x
        self.target_y = y

    def show_thought(self, text: str, duration_sec: int = 5):
        self.canvas.itemconfig(self.bubble, state="normal")
        self.canvas.itemconfig(self.bubble_text, state="normal", text=text)
        self.bubble_timer = int(duration_sec * 20)
        self.root.lift() # Ensure bubble is visible

    def update_visuals(self, color: str, intensity: float):
        try:
            h = color.lstrip('#')
            self.current_rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except: self.current_rgb = (0, 229, 255)
        self.intensity = max(0.2, min(1.0, intensity))

    def run_loop(self):
        while True:
            self.tick()
            time.sleep(0.05)

if __name__ == "__main__":
    ui = DesktopBrio()
    ui.run_loop()
