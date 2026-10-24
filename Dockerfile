FROM python:3.13-alpine
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_CACHE=1

WORKDIR /code
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY ./bot ./bot

CMD ["/code/.venv/bin/python", "-m", "bot.bot"]
