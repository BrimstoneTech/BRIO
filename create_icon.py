"""
create_icon.py

Converts the Sentinel Orb PNG into a professional multi-size Windows .ico file.
"""
from PIL import Image
import os

def generate_icon(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"[Error] Source image {input_path} not found.")
        return False
        
    print(f"[Info] Converting {input_path} to {output_path}...")
    img = Image.open(input_path)
    # Standard Windows icon sizes
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, format='ICO', sizes=icon_sizes)
    print("[Success] Icon generated successfully.")
    return True

if __name__ == "__main__":
    generate_icon("assets/orb_base.png", "assets/brio_icon.ico")
