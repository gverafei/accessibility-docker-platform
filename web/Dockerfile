FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    default-mysql-client \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app/ /app/

EXPOSE 5000

CMD ["python", "main.py"]