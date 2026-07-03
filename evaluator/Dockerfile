FROM node:20-alpine

WORKDIR /evaluator

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

ENV CHROME_PATH=/usr/bin/chromium-browser
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

COPY package.json /evaluator/package.json
COPY requirements.txt /evaluator/requirements.txt

RUN npm install

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

ENV PATH="/opt/venv/bin:${PATH}"

COPY . /evaluator/

EXPOSE 3000

CMD ["node", "server.js"]