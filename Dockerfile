FROM python:3.11.2-slim-bullseye

ARG TZ=America/New_York

VOLUME "/config"

RUN \
    pip install requests \
    && pip install python-telegram-bot==13.15 \
    && pip cache purge

RUN mkdir /app
COPY ./dme-update.py /app
RUN chmod 755 /app/dme-update.py

ENTRYPOINT [ "python3", "-u", "/app/dme-update.py" ]