FROM node:20-bookworm

WORKDIR /evaluator

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    chromium \
    && rm -rf /var/lib/apt/lists/*

COPY package.json /evaluator/package.json
COPY requirements.txt /evaluator/requirements.txt

RUN npm install
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY . /evaluator/

EXPOSE 3000

CMD ["node", "server.js"]