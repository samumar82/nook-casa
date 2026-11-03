FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core tzdata && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir Pillow==11.3.0
WORKDIR /app
COPY server.py /app/server.py
ENV PYTHONUNBUFFERED=1
CMD ["python3", "/app/server.py"]
