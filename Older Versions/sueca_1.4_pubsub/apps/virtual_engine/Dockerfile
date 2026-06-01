FROM python:3.11-slim
WORKDIR /app
COPY apps/virtual_engine/requirements.txt /tmp/virtual-engine-requirements.txt
RUN pip install --no-cache-dir -r /tmp/virtual-engine-requirements.txt
COPY apps /app/apps
COPY shared /app/shared
EXPOSE 5000
CMD ["uvicorn", "apps.virtual_engine.api:app", "--host", "0.0.0.0", "--port", "5000"]
    