FROM resin/raspberrypi3-debian:jessie

WORKDIR /usr/src/app/
ENV INITSYSTEM on

RUN apt-get update && \
    apt-get install -yq \
      avahi-daemon avahi-utils libnss-mdns

RUN systemctl enable avahi-daemon

COPY nsswitch.conf /etc/nsswitch.conf

CMD avahi-browse -a

FROM python:3

WORKDIR /the/workdir/path

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./run.py"]

