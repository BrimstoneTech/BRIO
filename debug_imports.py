
try:
    import numpy as np
    print("[PASS] numpy")
except ImportError as e:
    print(f"[FAIL] numpy: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("[PASS] sentence-transformers")
except ImportError as e:
    print(f"[FAIL] sentence-transformers: {e}")
except Exception as e:
    print(f"[FAIL] sentence-transformers crash: {e}")
