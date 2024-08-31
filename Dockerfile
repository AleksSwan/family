# syntax = docker/dockerfile:1.2
FROM python:3.12-bullseye
RUN apt-get update && apt-get -y upgrade && apt-get -y install gcc && apt-get install -y netcat-openbsd


WORKDIR /app

ARG poetryargs="--only main"
ARG GID=1000
ARG UID=1000
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip3 install --upgrade pip
RUN pip3 install poetry

RUN addgroup --gid $GID --system app && \
    adduser --no-create-home --shell /bin/false --disabled-password --uid $UID --system --group app

COPY poetry.lock pyproject.toml /app/


RUN poetry config virtualenvs.create false && \
    poetry install -vvv ${poetryargs} --no-interaction --no-ansi --no-root

RUN mkdir -p src/app
RUN touch src/app/__init__.py

RUN pip install -vvv -e . # Install my app

COPY --chown=app migrations /app/migrations/
COPY --chown=app alembic.ini /app/alembic.ini
COPY --chown=app tests /app/tests/

USER app
