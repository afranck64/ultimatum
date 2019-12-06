FROM python:3.6-slim-jessie

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

WORKDIR /code
COPY . .
RUN cd /code

ENV FLASK_APP survey.app
ENV FLASK_RUN_HOST 0.0.0.0
ENV TXX=true

CMD ["gunicorn", "-b 0.0.0.0:5000", "survey.app:app"]