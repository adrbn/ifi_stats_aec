"""
Icon converter helper — run during Windows build to produce oscar.ico
Requires: pip install pillow
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, "IFI_noir_logo.png")
dst = os.path.join(ROOT, "build", "icons", "oscar.ico")

os.makedirs(os.path.dirname(dst), exist_ok=True)

try:
    from PIL import Image
    img = Image.open(src).convert("RGBA")
    sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
    img.save(dst, format="ICO", sizes=sizes)
    print(f"Saved: {dst}")
except ImportError:
    print("Pillow not installed; skipping .ico conversion. Run: pip install pillow")
    sys.exit(0)
except Exception as e:
    print(f"Icon conversion failed: {e}")
    sys.exit(1)
