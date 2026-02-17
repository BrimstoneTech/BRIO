
print("Importing PIL...")
try:
    from PIL import Image
    print("PIL imported successfully.")
except Exception as e:
    print(f"PIL import failed: {e}")

print("Initializing Image...")
try:
    img = Image.new('RGB', (100, 100))
    print("Image created.")
except Exception as e:
    print(f"Image creation failed: {e}")
