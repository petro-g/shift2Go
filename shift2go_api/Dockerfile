FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

RUN echo $HOST
RUN echo $PORT

COPY ./app /app

WORKDIR /app

RUN apt update && \
    apt install -y postgresql-client

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .