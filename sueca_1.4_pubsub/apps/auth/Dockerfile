FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r apps/auth/requirements.txt
ENV PYTHONPATH=/app
EXPOSE 5010
CMD ["uvicorn", "apps.auth.main:app", "--host", "0.0.0.0", "--port", "5010"]
