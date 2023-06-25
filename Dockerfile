FROM ubuntu:latest

RUN apt update -y && \
    apt install python3 python3-requests --no-install-recommends -y && \
    apt clean

WORKDIR /ddns
copy update.py .
CMD python3 update.py
