FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and other libraries
RUN apt-get update && apt-get install -y \
    libxcb1 \
    libx11-6 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libglib2.0-0 \
    libfontconfig1 \
    libgl1-mesa-dri \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY apps/hybrid_engine/requirements.txt /tmp/hybrid-engine-requirements.txt
RUN pip install --no-cache-dir -r /tmp/hybrid-engine-requirements.txt

# Copy application code
COPY apps /app/apps
COPY shared /app/shared

EXPOSE 8002

ENV PYTHONPATH=/app
ENV HYBRID_CV_MODEL_PATH=/app/apps/hybrid_engine/cv/best.pt
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics

CMD ["uvicorn", "apps.hybrid_engine.main:app", "--host", "0.0.0.0", "--port", "8002"]
