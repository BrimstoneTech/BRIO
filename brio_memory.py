
import os
import time
import json
import math

DEPENDENCIES_OK = True
USE_CHROMA = False

# Try imports
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import fitz  # PyMuPDF
    from bs4 import BeautifulSoup # HTML Processing
except ImportError as e:
    print(f"[BrioMemory] CRITICAL: Missing dependency {e}. Local RAG will not function.")
    DEPENDENCIES_OK = False

# Try ChromaDB (known to fail on Python 3.14)
if DEPENDENCIES_OK:
    try:
        import chromadb
        USE_CHROMA = True
    except Exception as e:
        print(f"[BrioMemory] ChromaDB not available ({e}). Using SimpleVectorStore.")
        USE_CHROMA = False

class SimpleVectorStore:
    """A lightweight JSON-based vector store fallback for ChromaDB."""
    def __init__(self, path="brio_memory_simple.json"):
        self.path = path
        self.documents = [] # List of strings
        self.metadatas = [] # List of dicts
        self.embeddings = [] # List of numpy arrays (or lists)
        self.ids = [] 
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', [])
                    self.metadatas = data.get('metadatas', [])
                    self.ids = data.get('ids', [])
                    # Embeddings are stored as lists in JSON, convert to numpy if needed or keep as lists
                    self.embeddings = data.get('embeddings', [])
            except Exception as e:
                print(f"[SimpleVectorStore] Load error: {e}")

    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({
                    'documents': self.documents,
                    'metadatas': self.metadatas,
                    'embeddings': self.embeddings, # JSON serializes lists fine
                    'ids': self.ids
                }, f)
        except Exception as e:
             print(f"[SimpleVectorStore] Save error: {e}")

    def add(self, documents, metadatas, ids, embeddings=None):
        # Determine start index to avoid duplicates if ID exists? 
        # For simplicity, we append. Real Chroma handles ID collision.
        # We will check if ID exists and update.
        for i, doc_id in enumerate(ids):
            if doc_id in self.ids:
                idx = self.ids.index(doc_id)
                self.documents[idx] = documents[i]
                self.metadatas[idx] = metadatas[i]
                if embeddings is not None:
                     self.embeddings[idx] = embeddings[i]
            else:
                self.ids.append(doc_id)
                self.documents.append(documents[i])
                self.metadatas.append(metadatas[i])
                if embeddings is not None:
                    self.embeddings.append(embeddings[i])
        self.save()

    def query(self, query_embeddings, n_results=3):
        # Manual cosine similarity
        results = {'documents': [], 'metadatas': [], 'distances': []}
        
        if not self.embeddings or not query_embeddings:
            return results

        q_vec = np.array(query_embeddings[0]) # Assume single query
        
        # Calculate scores
        scores = []
        for i, emb in enumerate(self.embeddings):
            vec = np.array(emb)
            # Cosine Sim: dot(a, b) / (norm(a) * norm(b))
            norm_q = np.linalg.norm(q_vec)
            norm_v = np.linalg.norm(vec)
            if norm_q == 0 or norm_v == 0:
                sim = 0
            else:
                sim = np.dot(q_vec, vec) / (norm_q * norm_v)
            scores.append((sim, i))
        
        # Sort desc
        scores.sort(key=lambda x: x[0], reverse=True)
        
        top_k = scores[:n_results]
        
        # Format like Chroma: list of lists
        docs = [self.documents[idx] for _, idx in top_k]
        metas = [self.metadatas[idx] for _, idx in top_k]
        dists = [1.0 - sim for sim, _ in top_k] # Chroma returns distance (lower better for L2, but here we used Cosine Sim. Chroma default is L2. We'll just return distance as 1-sim)
        
        results['documents'] = [docs]
        results['metadatas'] = [metas]
        results['distances'] = [dists]
        
        return results

    def count(self):
        return len(self.documents)

    def get_or_create_collection(self, name):
        return self # We act as the collection itself

class BrioMemoryEngram:
    def __init__(self, knowledge_path="brio_knowledge"):
        self.encoder = None
        self.collection = None
        self.client = None
        self.knowledge_path = knowledge_path

        if not DEPENDENCIES_OK:
            return

        try:
            print("[BrioMemory] Loading SentenceTransformer model...")
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2') 
            print("[BrioMemory] Model loaded.")

            if USE_CHROMA:
                self.client = chromadb.PersistentClient(path="brio_memory_db")
                self.collection = self.client.get_or_create_collection("brio_engram")
                print("[BrioMemory] Using ChromaDB.")
            else:
                self.client = SimpleVectorStore() # Acts as client
                self.collection = self.client # And collection
                print("[BrioMemory] Using SimpleVectorStore (JSON).")
                
        except Exception as e:
            print(f"[BrioMemory] Init Error: {e}")
        
    def absorb_knowledge(self):
        if not self.collection: return

        print("Brio is studying his knowledge engrams...")
        count_added = 0
        
        for root, dirs, files in os.walk(self.knowledge_path):
            for file in files:
                filepath = os.path.join(root, file)
                text = self._extract_text(filepath)
                
                if text:
                    chunks = self._chunk_text(text)
                    if not chunks: continue
                    
                    # Generate embeddings (must be list of lists for Chroma/JSON)
                    embeddings = self.encoder.encode(chunks).tolist()
                    
                    ids = [f"{file}_{i}_{int(time.time())}" for i in range(len(chunks))]
                    metadatas = [{
                        "source": file,
                        "path": filepath,
                        "chunk_id": i,
                        "type": self._get_file_type(file)
                    } for i in range(len(chunks))]
                    
                    self.collection.add(
                        documents=chunks,
                        embeddings=embeddings, 
                        metadatas=metadatas,
                        ids=ids
                    )
                    count_added += len(chunks)
                    
        print(f"Brio has memorized {count_added} new knowledge fragments!")
        if not USE_CHROMA:
             self.collection.save()
    
    def _extract_text(self, filepath):
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.pdf':
                doc = fitz.open(filepath)
                return " ".join([page.get_text() for page in doc])
            elif ext in ('.html', '.htm'):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    soup = BeautifulSoup(f.read(), 'lxml')
                    # Remove scripts and styles
                    for script_or_style in soup(["script", "style"]):
                        script_or_style.decompose()
                    return soup.get_text(separator=' ')
            elif ext in ('.txt', '.md', '.py', '.json'):
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            print(f"[BrioMemory] Failed to read {filepath}: {e}")
        return None
    
    def _chunk_text(self, text, chunk_size=500, overlap=50):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap 
        return chunks
    
    def _get_file_type(self, filename):
        return os.path.splitext(filename)[1].lower()

    def recall(self, query, n_results=3):
        if not self.collection or not self.encoder: return [], []

        try:
            query_vector = self.encoder.encode(query).tolist()
            
            # Chroma expects list of embeddings
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=n_results
            )
            
            if results and results.get('documents') and len(results['documents']) > 0:
                return results['documents'][0], results['metadatas'][0]
        except Exception as e:
            print(f"[BrioMemory] Recall Error: {e}")
            
        return [], []
