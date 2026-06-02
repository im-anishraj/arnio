FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       cmake \
       ninja-build \
       git \
       bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Keep default command lightweight; dependency install happens in compose command
CMD ["bash"]
