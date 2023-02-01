FROM python:3.11-alpine

ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

COPY ./bot ./bot

CMD ["python","-m","bot.bot"]
