
import py_compile
import os
import sys

files = [
    "brio_main.py",
    "brio_brain.py",
    "brio_memory.py",
    "brio_mind.py",
    "verify_rag.py"
]

print("--- Source Code Integrity Check ---")
errors = False
for f in files:
    if not os.path.exists(f):
        print(f"[MISSING] {f}")
        errors = True
        continue
        
    try:
        py_compile.compile(f, doraise=True)
        print(f"[OK] {f}")
    except py_compile.PyCompileError as e:
        print(f"[FAIL] {f}: {e}")
        errors = True
    except Exception as e:
        print(f"[FAIL] {f}: {e}")
        errors = True

if not errors:
    print("\n[SUCCESS] All core modules compiled successfully.")
    sys.exit(0)
else:
    print("\n[FAIL] Syntax errors detected.")
    sys.exit(1)
