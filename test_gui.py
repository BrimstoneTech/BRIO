"""
Minimal test to see what's causing Brio to close
"""
import sys
from PyQt5.QtWidgets import QApplication

print("Step 1: Imports successful")

try:
    from brio_desktop_ui import DesktopBrio
    print("Step 2: DesktopBrio imported")
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    print("Step 3: QApplication created")
    
    def dummy_callback(cmd):
        print(f"Command received: {cmd}")
        return "OK"
    
    ui = DesktopBrio(command_callback=dummy_callback)
    print("Step 4: DesktopBrio instantiated")
    
    ui.show()
    print("Step 5: UI shown")
    
    print("Step 6: Entering event loop...")
    sys.exit(app.exec_())
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")


