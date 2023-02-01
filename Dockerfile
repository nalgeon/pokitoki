FROM python:3.11-alpine

WORKDIR /code
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

COPY ./bot ./bot

CMD ["python","-m","bot.bot"]
