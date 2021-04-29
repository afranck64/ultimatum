# syntax=docker/dockerfile:experimental

FROM python:3.8-slim-buster

COPY requirements.txt requirements.txt
COPY requirements-test.txt requirements-test.txt

RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt -r requirements-test.txt

WORKDIR /code
COPY . .
RUN cd /code

ENV FLASK_APP survey.app
ENV FLASK_RUN_HOST 0.0.0.0
ENV TXX=true
ENV GUNICORN_BIND=0.0.0.0:5000

#CMD ["gunicorn", "--log-file out.log --log-level debug --error-logfile=- --workers 1 --reload --bind $GUNICORN_BIND", " --timeout 300", "survey.app:app"]
CMD ["gunicorn", "survey.app:app",  "--bind $GUNICORN_BIND", " --timeout 300"]