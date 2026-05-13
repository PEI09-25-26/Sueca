FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# Install system libraries required by OpenCV (libxcb and friends)
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

RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8001 8002
ENV PYTHONPATH=/app
CMD ["uvicorn", "apps.physical_engine.cv_service:app", "--host", "0.0.0.0", "--port", "8001"]
