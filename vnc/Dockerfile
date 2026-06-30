FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VNC_PASSWORD=testpass
ENV VNC_DISPLAY=:1
ENV VNC_GEOMETRY=1280x800
ENV VNC_DEPTH=24

RUN apt-get update && apt-get install -y \
    tigervnc-standalone-server \
    tigervnc-common \
    xfce4 \
    xfce4-terminal \
    dbus-x11 \
    x11-xserver-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash testuser

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# VNC standard
EXPOSE 5901

ENTRYPOINT ["/entrypoint.sh"]
