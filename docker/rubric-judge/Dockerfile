FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337
COPY judge.py /opt/sonar/judge.py
COPY --chmod=755 test.sh /tests/test.sh
WORKDIR /app
