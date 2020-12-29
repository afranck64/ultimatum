# syntax=docker/dockerfile:experimental

FROM python:3.8-slim-buster

COPY requirements.txt requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

WORKDIR /code
COPY . .
RUN cd /code

ENV FLASK_APP survey.app
ENV FLASK_RUN_HOST 0.0.0.0
ENV TXX=true

CMD ["gunicorn", "-b 0.0.0.0:5000", "survey.app:app"]