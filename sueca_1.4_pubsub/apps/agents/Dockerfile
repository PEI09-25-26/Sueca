FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r apps/agents/requirements.txt
ENV PYTHONPATH=/app
EXPOSE 5030
CMD ["uvicorn", "apps.agents.main:app", "--host", "0.0.0.0", "--port", "5030"]
