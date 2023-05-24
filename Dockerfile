FROM docker:dind
# docker in docker is needed to spawn docker container when running
# init docker

RUN apk add --update python3 py3-pip

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .

ENTRYPOINT /app/entrypoint.sh
