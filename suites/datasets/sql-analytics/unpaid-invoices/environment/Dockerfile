FROM sonar-eval/agents:1

RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY example.json schema.sql /app/
