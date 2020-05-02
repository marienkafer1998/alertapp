FROM python:3.7.7-alpine

WORKDIR /opt/app

ADD . /opt/app/.

RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev && \
    pip install -r requirements.txt

CMD ["python", "-u", "alertapp.py"]