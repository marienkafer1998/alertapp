FROM python:3.7.7-alpine

WORKDIR /opt/app

ADD . /opt/app/.

RUN pip install -r requirements.txt

CMD ["python", "alertapp.py"]