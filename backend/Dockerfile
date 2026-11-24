FROM python:3.12-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt
FROM python:3.12-slim AS test
COPY --from=builder /install/deps /usr/local
WORKDIR /app
COPY app ./app
COPY tests ./tests
ENV PYTHONPATH=/app
CMD ["pytest"]
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY --from=builder /install/deps /usr/local
WORKDIR /app
COPY app ./app
RUN mkdir -p /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
