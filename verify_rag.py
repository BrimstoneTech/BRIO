
import os
import sys
import requests
import importlib

def check_import(module_name):
    try:
        importlib.import_module(module_name)
        print(f"[PASS] {module_name}")
        return True
    except ImportError:
        print(f"[FAIL] {module_name} (Not Installed)")
        return False

def check_ollama():
    url = "http://127.0.0.1:11434"
    try:
        print(f"Connecting to {url}...")
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            print("[PASS] Ollama (Running)")
            return True
        else:
            print(f"[FAIL] Ollama (Status: {resp.status_code})")
            return False
    except Exception as e:
        print(f"[FAIL] Ollama Connection Error: {e}")
        print("       (If 'ollama serve' says 'Address already in use', then Ollama IS running but maybe not responding or firewall blocks it.)")
        return False

def check_knowledge():
    if os.path.exists("brio_knowledge"):
        print(f"[PASS] brio_knowledge directory found with {sum([len(files) for r, d, files in os.walk('brio_knowledge')])} files.")
        return True
    else:
        print("[FAIL] brio_knowledge directory missing")
        return False

print("--- Brio Local RAG Verification ---\n")

def check_vector_backend():
    # Check Chroma
    chroma_ok = False
    try:
        import chromadb
        print("[PASS] ChromaDB (Extended Vector Store)")
        chroma_ok = True
    except Exception as e:
        print(f"[INFO] ChromaDB unavailable ({e}). Checking fallback...")

    # Check Simple
    simple_ok = False
    try:
        import numpy
        from sentence_transformers import SentenceTransformer
        print("[PASS] SimpleVectorStore (Basic Local Vector Store)")
        simple_ok = True
    except ImportError as e:
        print(f"[FAIL] SimpleVectorStore unavailable: {e}")
    
    return chroma_ok or simple_ok

libs_ok = check_vector_backend() and check_import("requests") and check_import("fitz")

ollama_ok = check_ollama()
knowledge_ok = check_knowledge()

if libs_ok and ollama_ok and knowledge_ok:
    print("\n[SUCCESS] Local RAG System Ready!")
    sys.exit(0)
else:
    print("\n[WARNING] Some components are missing.")
    if not libs_ok: 
        print("Required for Fallback Store:")
        print("python -m pip install numpy sentence-transformers PyMuPDF requests")
    if not ollama_ok: print("Install & Run: https://ollama.com/")
    sys.exit(1)
