# BRIM AI - Requirements and Setup Guide

## Minimum Requirements

```
Python >= 3.7
No external packages required (uses only Python standard library)
```

## System Requirements

- **OS**: Windows, macOS, or Linux
- **Memory**: 50 MB minimum
- **Storage**: 10 MB for code + growing database

## Installation Steps

### 1. Clone/Download
```bash
# Navigate to BRIM AI directory
cd "c:\Users\Administrator\Documents\THESE ARE MY PROJECTS\BRIM AI"
```

### 2. Verify Python Installation
```bash
python --version
# Should output Python 3.7 or higher
```

### 3. Run BRIM
```bash
python LogicSimulatedEmotionsandFeelings.py
```

## Optional Dependencies for Enhanced Features

If you want to extend BRIM with machine learning or visualization:

```bash
# For machine learning (decision trees, neural networks)
pip install scikit-learn tensorflow

# For data visualization and analysis
pip install matplotlib plotly pandas numpy

# For web interface (optional)
pip install flask fastapi uvicorn

# For sentiment analysis (optional)
pip install textblob nltk

# For advanced database (optional)
pip install sqlalchemy
```

## Installation Commands by Feature

### Minimal Setup (No Dependencies)
```bash
# Just run the main file
python LogicSimulatedEmotionsandFeelings.py
```

### With Data Analysis
```bash
pip install pandas numpy matplotlib
python LogicSimulatedEmotionsandFeelings.py
```

### With ML Extensions
```bash
pip install scikit-learn pandas numpy
python LogicSimulatedEmotionsandFeelings.py
```

### Full Featured Setup
```bash
pip install scikit-learn tensorflow pandas numpy matplotlib plotly flask
python LogicSimulatedEmotionsandFeelings.py
```

## Project Structure

```
BRIM AI/
├── LogicSimulatedEmotionsandFeelings.py  (Main prototype - 500+ lines)
├── README.md                             (Feature documentation)
├── REQUIREMENTS.md                       (This file)
├── USAGE_GUIDE.md                        (Detailed usage examples)
├── brim_interactions.db                  (Generated - SQLite database)
└── brim_export.json                      (Generated - Export logs)
```

## Usage Quick Start

### Interactive Mode
```bash
python LogicSimulatedEmotionsandFeelings.py
```

### Programmatic Usage
```python
from LogicSimulatedEmotionsandFeelings import BRIM, BRIMInterface

# Direct usage
brim = BRIM()
response = brim.interact("Hello, can you help me?")
print(response)

# With feedback
brim.provide_feedback(0, 'positive')

# Get status
status = brim.get_status()
print(status)

# Export logs
brim.export_logs('my_logs.json')

# Generate report
print(brim.generate_report())
```

## File Description

### Core File: LogicSimulatedEmotionsandFeelings.py

**Size**: ~600 lines
**Components**:

1. **Emotion System** (200 lines)
   - EmotionType: 6 core emotions
   - EmotionTrigger: 8 trigger types
   - EmotionalState: State management with decay and transitions

2. **Cultural Knowledge** (50 lines)
   - Ugandan proverbs
   - Local humor
   - Cultural values

3. **Decision Engine** (100 lines)
   - Harm detection
   - Ethical validation
   - Confidence calculation
   - Task classification

4. **Learning System** (50 lines)
   - Feedback recording
   - Quality scoring
   - Emotional adjustment

5. **Core BRIM Class** (150 lines)
   - Main orchestration
   - Database integration
   - Interaction management
   - Logging and export

6. **CLI Interface** (80 lines)
   - Interactive loop
   - Command handling
   - User interface

## Database Files

### brim_interactions.db
**Created on**: First run
**Size**: Grows with interactions
**Tables**:
- `interactions`: User inputs, responses, feedback, emotions
- `emotional_timeline`: Emotional state snapshots

### brim_export.json
**Created on**: `export` command
**Format**: Human-readable JSON
**Contents**:
- Metadata (timestamps, final state)
- All interactions with full history
- Mood intensity timeline

## Performance Characteristics

- **Startup time**: < 100ms
- **Response time**: < 50ms per interaction
- **Database size**: ~1KB per interaction
- **Memory usage**: ~5-10 MB steady state
- **CPU usage**: Minimal (mostly I/O)

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'sqlite3'"
**Solution**: sqlite3 is included in Python stdlib. Update Python to 3.7+

### Issue: "Database is locked"
**Solution**: Close any other instances of BRIM; restart the application

### Issue: Emotional state not changing
**Solution**: This is normal after several interactions - emotions decay to baseline

### Issue: Commands not recognized
**Solution**: Type exactly (lowercase): `status`, `report`, `export`, `feedback:`, `proverb`, `help`, `quit`

## Environment Variables (Optional)

```bash
# Set custom database path
set BRIM_DB_PATH=C:\custom\path\brim.db
python LogicSimulatedEmotionsandFeelings.py

# Set log export directory
set BRIM_LOG_DIR=C:\logs
python LogicSimulatedEmotionsandFeelings.py
```

## Cross-Platform Notes

### Windows
```bash
python LogicSimulatedEmotionsandFeelings.py
# or
py LogicSimulatedEmotionsandFeelings.py
```

### macOS/Linux
```bash
python3 LogicSimulatedEmotionsandFeelings.py
```

## Getting Help

### Built-in Help
```
You: help
BRIM: [Shows command menu]
```

### View Logs
```bash
# On Windows
type brim_export.json | more

# On macOS/Linux
cat brim_export.json | less
```

### Debug Mode
```python
# Add to code for debugging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Extended Usage

### Running Batch Interactions
```python
from LogicSimulatedEmotionsandFeelings import BRIM

brim = BRIM('batch_test.db')

prompts = [
    "Hello, how are you?",
    "Can you help with Python?",
    "Great, thank you!",
    "What's your emotional state?",
]

for prompt in prompts:
    response = brim.interact(prompt)
    print(f"Q: {prompt}")
    print(f"A: {response}\n")

# Export results
brim.export_logs('batch_results.json')
print(brim.generate_report())
```

### Analyzing Emotional Patterns
```python
from LogicSimulatedEmotionsandFeelings import BRIM
import json

brim = BRIM()
brim.export_logs('analysis.json')

with open('analysis.json') as f:
    data = json.load(f)
    
# Analyze mood intensity over time
for entry in data['mood_history']:
    print(f"{entry['timestamp']}: {entry['intensity']:.2%}")
```

### Training BRIM with Feedback
```python
from LogicSimulatedEmotionsandFeelings import BRIM

brim = BRIM()

# Simulate training session
interactions = [
    ("What is Python?", "positive"),
    ("Help with lists", "positive"),
    ("Explain decorators", "positive"),
    ("Why does X fail?", "negative"),
    ("Can you help again?", "positive"),
]

for prompt, feedback in interactions:
    response = brim.interact(prompt)
    brim.provide_feedback(len(brim.interaction_history) - 1, feedback)

# View learning progress
adjustment = brim.learning_system.get_learning_adjustment()
print(f"Learning adjustment: {adjustment:.3f}")

# Emotions should reflect feedback pattern
print(brim.generate_report())
```

## Next Steps

1. **Run BRIM**: Execute the main file to start
2. **Explore Commands**: Try `status`, `report`, `proverb`
3. **Provide Feedback**: Use `feedback: positive/negative` to train
4. **Export Logs**: Use `export` to analyze interaction history
5. **Extend Features**: Customize emotions, triggers, and proverbs

## Support & Contribution

For enhancements or issues:
1. Review the README.md for feature documentation
2. Check the code comments (well-documented)
3. Extend BRIM by modifying emotion triggers and cultural elements
4. Export logs for analysis and validation

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Status**: Production-Ready for Prototyping
