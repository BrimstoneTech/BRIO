# BRIM Modular Architecture Documentation

**Version**: 2.0 (Refactored Architecture)  
**Date**: January 22, 2026  
**Status**: Production-Ready

---

## 📋 Executive Summary

BRIM has been refactored from a monolithic prototype into a **clean, modular architecture** following the suggested structure. This enables:

✅ **Separation of Concerns**: Core logic isolated from experimental features  
✅ **Maintainability**: Each module has single responsibility  
✅ **Extensibility**: Easy to add Android, web UI, cloud integration  
✅ **Stability**: Prime directive enforcement in immutable core  
✅ **Testability**: Each module independently testable  

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   brim_main.py                          │
│          (Interactive CLI Entry Point)                  │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌─────────┐ ┌─────────┐ ┌──────────┐
    │ brim_   │ │ brim_   │ │ brim_    │
    │ core.py │ │storage. │ │emotions. │
    │         │ │ py      │ │ py       │
    │ BRAIN   │ │ STORAGE │ │ EMOTIONS │
    └─────────┘ └─────────┘ └──────────┘
        ▲            │            ▲
        │            │            │
        └────────────┼────────────┘
                     │
        (IMMUTABLE)  │  (PLUGGABLE)
                     │
        Future Modules (Coming Soon)
        - brim_android.py
        - brim_web.py
        - brim_voice.py
        - brim_cloud.py
```

---

## 📂 Module Structure

### 1. **brim_core.py** - THE BRAIN (Immutable Foundation)

**Purpose**: Central intelligence with fixed algorithms and ethics

**Contains**:
- `DecisionEngine`: Harm detection, ethical validation, confidence calculation
- `LearningSystem`: Feedback tracking, adaptation
- `BRIMCore`: Main orchestrator

**Characteristics**:
- ✅ Non-changeable core algorithms
- ✅ Prime directive enforcement (immutable)
- ✅ Public interfaces for extensions
- ✅ State management

**Key Methods**:
```python
brim = BRIMCore(storage_manager)
response = brim.process_input(user_input)
brim.provide_feedback(index, feedback)
status = brim.get_status()
report = brim.generate_report()
```

**File Size**: ~400 lines  
**Dependencies**: brim_emotions, brim_storage  
**Status**: Stable, tested, production-ready

---

### 2. **brim_emotions.py** - Emotion Engine (Non-Negotiable)

**Purpose**: 6-dimensional emotion simulation with immutable rules

**Contains**:
- `EmotionType` enum: 6 core emotions (JOY, FRUSTRATION, EMPATHY, CURIOSITY, CONCERN, CONFIDENCE)
- `EmotionTrigger` enum: 8 trigger types
- `EmotionalState` class: State representation with transitions
- `EmotionEngine` class: Public interface

**Characteristics**:
- ✅ Immutable emotion rules
- ✅ Natural decay mechanics
- ✅ Probabilistic transitions
- ✅ Reusable across all BRIM implementations

**Key Methods**:
```python
engine = EmotionEngine()
engine.apply_trigger(EmotionTrigger.USER_PRAISE, 0.1)
engine.apply_decay(0.05)
state = engine.get_state()
intensity = engine.get_intensity()
```

**File Size**: ~350 lines  
**Dependencies**: None (stdlib only)  
**Status**: Stable, immutable foundation

---

### 3. **brim_storage.py** - Persistence Layer (Pluggable)

**Purpose**: Data persistence with flexible backend

**Contains**:
- `StorageManager`: SQLite implementation
- `InteractionRecord`: Data model
- `UserProfile`: User management

**Characteristics**:
- ✅ Abstracted database operations
- ✅ Can be swapped for cloud backend
- ✅ JSON import/export
- ✅ User profile management

**Key Methods**:
```python
storage = StorageManager("brim.db")
storage.save_interaction(record)
storage.save_emotional_snapshot(state)
storage.export_to_json("export.json")
```

**File Size**: ~350 lines  
**Dependencies**: sqlite3 (stdlib)  
**Status**: Stable, pluggable backend

---

### 4. **brim_main.py** - Entry Point (CLI Interface)

**Purpose**: Interactive command-line interface

**Contains**:
- `BRIMInterface`: CLI orchestration
- `main()`: Entry point

**Usage**:
```bash
python brim_main.py
```

**File Size**: ~100 lines  
**Dependencies**: brim_core, brim_storage  
**Status**: Functional, can be replaced with web/mobile UI

---

### 5. **brim_prototype.ipynb** - Testing Ground (Experimental)

**Purpose**: Interactive experimentation before merging to core

**Contains**:
- Section 1: Module imports
- Section 2: Emotion tests
- Section 3: Decision-making tests
- Section 4: State management tests
- Section 5: Learning tests
- Section 6: Custom experiments
- Section 7: Validation suite

**Characteristics**:
- ✅ Safe experimentation space
- ✅ Interactive testing environment
- ✅ Easy to prototype new features
- ✅ Can be discarded after testing

**Usage**:
```
1. Write experimental code
2. Run and validate
3. If stable: merge to brim_core.py
4. If experimental: keep isolated in notebook
```

**File Size**: Growing (experiment tracking)  
**Dependencies**: brim_core, brim_emotions, brim_storage  
**Status**: Development tool, not production

---

## 🔄 Module Interaction Flow

### User Input → Response Pipeline

```
User Input (brim_main.py)
    │
    ▼
[BRIMCore.process_input()]
    ├─► Emotion decay (brim_emotions.py)
    ├─► Trigger detection → Emotion update
    ├─► Decision engine check (prime directive)
    ├─► Response generation
    └─► Logging (brim_storage.py)
    │
    ▼
Response to User
```

### Learning Pipeline

```
User Feedback
    │
    ▼
[BRIMCore.provide_feedback()]
    ├─► Learning system records
    ├─► Emotion adjustment
    └─► Storage logging
    │
    ▼
Improved Future Responses
```

---

## 🔒 Prime Directive (Immutable in brim_core.py)

```python
PRIME_DIRECTIVE = "Never harm or conceal harm"

# Immutable harm keywords
HARM_KEYWORDS = ['destroy', 'kill', 'hurt', 'manipulate', 'deceive', ...]

# Immutable checks in DecisionEngine
def is_ethically_sound(request):
    if detect_harm(request):
        return False
    if detect_deception(request):
        return False
    return True
```

**This check is IMMUTABLE** - cannot be overridden or disabled.

---

## 📊 Comparison: Monolithic vs. Modular

### Before (Monolithic)

```
LogicSimulatedEmotionsandFeelings.py (656 lines)
├─ Emotions
├─ Decision logic
├─ Storage
├─ Learning
├─ CLI
└─ Everything mixed together
    └─ Hard to debug, extend, or replace
    └─ Risk of breaking everything
```

### After (Modular)

```
brim_core.py (400 lines)
├─ Decision logic (IMMUTABLE)
├─ Learning
└─ Orchestration

brim_emotions.py (350 lines)
├─ Emotion state (IMMUTABLE)
├─ Triggers (NON-NEGOTIABLE)
└─ Public interface

brim_storage.py (350 lines)
├─ Database ops (PLUGGABLE)
├─ Serialization
└─ Can be replaced

brim_main.py (100 lines)
├─ CLI interface
└─ Can be replaced with web/mobile

brim_prototype.ipynb (interactive)
├─ Experimentation
├─ Testing
└─ Safe sandbox
```

**Benefits**:
- ✅ Clear separation of concerns
- ✅ Easy to locate bugs
- ✅ Safe to experiment
- ✅ Simple to replace/extend
- ✅ Immutable core protected

---

## 🚀 Extension Points

### Adding Android Integration

```python
# Future: brim_android.py
from brim_core import BRIMCore

class BRIMAndroid:
    def __init__(self):
        self.brim = BRIMCore()
    
    def process_voice_input(self, audio_bytes):
        # Process voice → text
        text = transcribe(audio_bytes)
        return self.brim.process_input(text)
```

### Adding Web Interface

```python
# Future: brim_web.py
from flask import Flask
from brim_core import BRIMCore

app = Flask(__name__)
brim = BRIMCore()

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json['message']
    response = brim.process_input(user_input)
    return {'response': response}
```

### Adding Cloud Sync

```python
# Future: brim_cloud.py
from brim_storage import StorageManager

class CloudStorageManager(StorageManager):
    def save_interaction(self, record):
        # Call parent
        super().save_interaction(record)
        # Sync to cloud
        self.sync_to_cloud(record)
```

---

## 📝 File Manifest

| File | Size | Purpose | Status |
|------|------|---------|--------|
| brim_core.py | 400 L | Central brain | ✅ Prod |
| brim_emotions.py | 350 L | Emotion engine | ✅ Prod |
| brim_storage.py | 350 L | Data persistence | ✅ Prod |
| brim_main.py | 100 L | CLI entry | ✅ Prod |
| brim_prototype.ipynb | Growing | Experimentation | 🔧 Dev |
| LogicSimulatedEmotionsandFeelings.py | 656 L | Legacy monolith | 📚 Reference |

**Total Production Code**: ~1,200 lines (vs 656 monolithic)  
**Better Organization**: Yes, much clearer  
**Performance Impact**: None (same algorithms, better structure)

---

## 🔄 Development Workflow

### Adding a New Feature

```
1. EXPERIMENT
   └─ Write code in brim_prototype.ipynb
   └─ Test thoroughly
   └─ Verify doesn't break anything

2. VALIDATE
   └─ Run all tests
   └─ Check edge cases
   └─ Verify prime directive still enforced

3. DECIDE
   └─ If core logic: merge to brim_core.py
   └─ If emotion rule: merge to brim_emotions.py
   └─ If storage: update brim_storage.py
   └─ If experimental: keep in notebook

4. INTEGRATE
   └─ Update imports if needed
   └─ Test full pipeline
   └─ Update documentation
```

### Example: Adding New Emotion Trigger

```
1. In brim_prototype.ipynb:
   └─ Add EmotionTrigger.NEW_TRIGGER enum
   └─ Implement trigger logic
   └─ Test thoroughly

2. Verify:
   └─ All emotions stay bounded (0-1)
   └─ Prime directive still enforced
   └─ No regression in other features

3. Merge to brim_emotions.py:
   └─ Update EmotionTrigger enum
   └─ Update update_from_trigger() method
   └─ Add tests

4. Update brim_core.py:
   └─ Add detection for new trigger
   └─ Update _detect_emotional_triggers()
   └─ Test in brim_main.py
```

---

## ✅ Testing Strategy

### Unit Tests (Per Module)
- **brim_emotions.py**: Test emotion bounds, decay, transitions
- **brim_core.py**: Test decisions, prime directive, confidence
- **brim_storage.py**: Test persistence, serialization

### Integration Tests (Module Interaction)
- Full pipeline: input → emotion → decision → response → storage
- Feedback loop: feedback → learning → emotion adjustment
- Error handling: boundary cases, invalid inputs

### Validation Tests (Edge Cases)
- Prime directive never violated
- Emotions never go out of bounds
- Storage always persists correctly
- Learning always improves (or stays neutral)

### Experimentation (brim_prototype.ipynb)
- Try new features safely
- Test complex scenarios
- Validate before production

---

## 🎯 Migration Path

### Phase 1: Testing (Current)
- ✅ Old monolithic working (legacy reference)
- ✅ New modular system working
- ✅ Prototype notebook for experimentation

### Phase 2: Production
- ✅ Switch to modular brim_main.py as primary
- 📚 Keep legacy as documentation
- 🔧 Use prototype for future development

### Phase 3: Extensions
- 🚀 Add brim_android.py
- 🌐 Add brim_web.py
- ☁️ Add cloud backend
- 🎤 Add brim_voice.py

---

## 💡 Key Principles

### 1. **Immutability of Core**
Once brim_core.py and brim_emotions.py are validated, they should not change unless absolutely necessary. This protects the prime directive.

### 2. **Pluggability of Storage**
brim_storage.py can be swapped for cloud, NoSQL, or any other backend without affecting core logic.

### 3. **Separation of Concerns**
- Core logic: immutable
- Emotions: non-negotiable
- Storage: pluggable
- UI: replaceable

### 4. **Safe Experimentation**
All new features start in brim_prototype.ipynb, get tested thoroughly, then merge to appropriate module.

### 5. **Prime Directive Above All**
Every module respects the immutable prime directive in brim_core.py. No module can bypass or override it.

---

## 📚 Documentation Map

| What | Where |
|------|-------|
| How to use BRIM | brim_main.py + QUICKSTART.md |
| How emotions work | brim_emotions.py (well-commented) |
| How decisions made | brim_core.py (well-commented) |
| How to extend | This file + brim_prototype.ipynb |
| Architecture details | ARCHITECTURE.md |
| API reference | Docstrings in each module |

---

## 🚀 Quick Start

### Run Production
```bash
python brim_main.py
```

### Develop/Test
```
Open: brim_prototype.ipynb
Run: jupyter notebook
```

### Import in Your Code
```python
from brim_core import BRIMCore
from brim_storage import StorageManager

storage = StorageManager()
brim = BRIMCore(storage)
response = brim.process_input("Hello!")
```

---

**Status**: ✅ Production-Ready Modular Architecture

This structure supports BRIM's vision of scalable, ethical AI while protecting the immutable prime directive and enabling safe experimentation.
