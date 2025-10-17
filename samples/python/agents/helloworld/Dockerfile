FROM ubuntu:24.04
WORKDIR helloworld
COPY . .
RUN apt update
RUN apt install -y python3 python3-pip
RUN pip install --break-system-packages uvicorn a2a-sdk a2a-sdk[http-server]
