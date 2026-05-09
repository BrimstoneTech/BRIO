FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Create audio output directory
RUN mkdir -p static/audio

# Expose port for HF Spaces
EXPOSE 7860

# Run BRIO
CMD ["python", "app.py"]
