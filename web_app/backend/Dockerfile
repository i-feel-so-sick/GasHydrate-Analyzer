FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:/app/web_app/backend

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY web_app/backend/requirements.txt /tmp/backend-requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY web_app/backend /app/web_app/backend

CMD ["python", "web_app/backend/run.py"]
