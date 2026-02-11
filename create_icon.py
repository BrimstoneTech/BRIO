"""
create_icon.py

Converts the Sentinel Orb PNG into a professional multi-size Windows .ico file.
"""
from PIL import Image
import os

def generate_icon(input_path, output_path):
    # Ensure assets directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if os.path.exists(input_path):
        print(f"[Info] Converting {input_path} to {output_path}...")
        img = Image.open(input_path)
    else:
        print(f"[Info] Source missing. Generating procedural Brio icon...")
        # Create a signature 512x512 canvas
        img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        # Brio Signature Light Blue (#70D6FF)
        color = (112, 214, 255, 255)
        # Draw the Orb
        draw.ellipse((40, 40, 472, 472), fill=color)
        # Add a subtle inner glow/pupil for character
        draw.ellipse((180, 180, 332, 332), fill=(255, 255, 255, 180))
        
    # Standard Windows icon sizes
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(output_path, format='ICO', sizes=icon_sizes)
    print(f"[Success] Brio v3.0 Icon ready at {output_path}")
    return True

if __name__ == "__main__":
    generate_icon("assets/orb_base.png", "assets/brio_icon.ico")
