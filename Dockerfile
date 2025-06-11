# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.7

FROM python:${PYTHON_VERSION}-slim

LABEL fly_launch_runtime="flask"

WORKDIR /code

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

ENV FLASK_APP=app.py

EXPOSE 8080

CMD ["python3", "app.py"]
