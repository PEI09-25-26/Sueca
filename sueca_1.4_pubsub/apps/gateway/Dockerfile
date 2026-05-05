FROM python:3.11-slim
WORKDIR /app
COPY apps/gateway/requirements.txt /tmp/gateway-requirements.txt
RUN pip install --no-cache-dir -r /tmp/gateway-requirements.txt
COPY apps /app/apps
COPY shared /app/shared
ENV PYTHONPATH=/app
EXPOSE 8080
ENV SUECA_AUTOSTART_SERVICES=0
CMD ["uvicorn", "apps.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
