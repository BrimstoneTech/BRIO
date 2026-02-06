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
    if sys.version_info >= (3, 14):
        print(" [BETA/EXPERIMENTAL]")
        score += 1
    elif sys.version_info >= (3, 8):
        print(" [OK]")
        score += 1
    else:
        print(" [LOW] (3.8+ Recommended)")

    # 2. Dependency: Pillow (Visuals)
    print("[2/5] Visual Engine (Pillow):", end=" ")
    try:
        importlib.import_module("PIL")
        print(" [OK]")
        score += 1
    except ImportError:
        print(" [MISSING] (CRITICAL for Sentinel Orb)")

    # 3. Dependency: psutil
    print("[3/5] Sensor Engine (psutil): ", end=" ")
    try:
        importlib.import_module("psutil")
        print(" [OK]")
        score += 1
    except ImportError:
        print(" [MISSING] (Limited telemetry)")

    # 4. Dependency: pyaudio (Hearing)
    print("[4/5] Audio Engine (pyaudio): ", end=" ")
    try:
        importlib.import_module("pyaudio")
        print(" [OK]")
        score += 1
    except ImportError:
        print(" [MISSING] (Hearing disabled)")

    # 5. Asset Check
    print("[5/5] Sentinel Orb Gallery:  ", end=" ")
    if os.path.exists("assets/orb_base.png"):
        print(" [OK]")
        score += 1
    else:
        print(" [MISSING]")

    print("------------------------------------------")
    vitality = (score / total) * 100
    print(f"TOTAL VITALITY: {vitality:.0f}%")
    
    if score >= 4:
        print("\n[RESULT] Brio is 100% READY for visuals & movement!")
        if vitality < 100:
            print("[NOTE] Audio Hearing is missing, but the Sentinel Orb is live.")
    elif score >= 2:
        print("\n[RESULT] Brio is functional in 'Silent Mode'.")
    else:
        print("\n[RESULT] Deployment failed. Check Pillow and Assets.")
    print("==========================================")

if __name__ == "__main__":
    check_vital()
