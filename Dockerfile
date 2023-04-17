FROM python:3.11-alpine

ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code
# tiktoken comes precompiled only for 64 bit targets.
# On other targets we have to compile it with rust
RUN grep -q 64 /etc/apk/arch || { \
    apk add cargo rust && \
    rm /var/cache/apk/* ; }
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

COPY ./bot ./bot

CMD ["python","-m","bot.bot"]
