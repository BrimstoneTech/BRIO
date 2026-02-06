"""
check_vitality.py

Automated Health Check for Brio v2.0
Verifies Python version, Dependencies, and Visual Assets.
"""

import sys
import os
import importlib

def check_vital":
    print("==========================================")
    print("       BRIO V2.0 VITALITY CHECK           ")
    print("==========================================")
    
    score = 0
    total = 5

    # 1. Python Check
    print(f"[1/5] Python Version: {sys.version.split()[0]}", end=" ")
    if sys.version_info >= (3, 8):
        print(" [OK]")
        score += 1
    else:
        print(" [LOW] (3.8+ Recommended)")

    # 2. Dependency: Pillow
    print("[2/5] Visual Engine (Pillow):", end=" ")
    try:
        importlib.import_module("PIL")
        print(" [OK]")
        score += 1
    except ImportError:
        print(" [MISSING] (Run setup.bat)")

    # 3. Dependency: psutil
    print("[3/5] Sensor Engine (psutil): ", end=" ")
    try:
        importlib.import_module("psutil")
        print(" [OK]")
        score += 1
    except ImportError:
        print(" [MISSING] (Brio will run in limited mode)")

    # 4. Asset Check
    print("[4/5] Sentinel Orb Asset:    ", end=" ")
    if os.path.exists("assets/orb_base.png"):
        print(" [OK]")
        score += 1
    else:
        print(" [MISSING] (Brio will use vector fallback)")

    # 5. Core Files
    print("[5/5] Core Brain (Main Loop): ", end=" ")
    if os.path.exists("brim_main.py"):
        print(" [OK]")
        score += 1
    else:
        print(" [MISSING]")

    print("------------------------------------------")
    vitality = (score / total) * 100
    print(f"TOTAL VITALITY: {vitality:.0f}%")
    
    if vitality == 100:
        print("\n[RESULT] Brio is 100% READY for deployment!")
    elif score >= 3:
        print("\n[RESULT] Brio is functional but limited. Check missing items.")
    else:
        print("\n[RESULT] Critical issues detected. Please run setup.bat.")
    print("==========================================")

if __name__ == "__main__":
    check_vital()
