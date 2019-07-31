FROM python:3.7

WORKDIR /build

COPY requirements*.txt /build/

RUN ["pip", "install", "-r", "requirements.txt", "-r", "requirements.build_test.txt"]