# Optional public-base environment; see docs/IMAGE.md for the actual tested image.
FROM docker.io/nvidia/cuda:12.9.1-devel-ubuntu24.04@sha256:020bc241a628776338f4d4053fed4c38f6f7f3d7eb5919fecb8de313bb8ba47c
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3.12-venv python3-pip git curl ca-certificates \
    build-essential ninja-build pkg-config libssl-dev libffi-dev libgomp1 util-linux ripgrep \
    zstd xz-utils unzip \
 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/elan /shared /opt/submission
RUN curl --fail --location --retry 3 \
      https://github.com/leanprover/elan/releases/download/v4.2.4/elan-x86_64-unknown-linux-gnu.tar.gz \
      --output /tmp/elan.tar.gz \
 && echo '42b94d4244e8353142c456ec0e4ca6528fd898a6c604d4059f494e706e431f63  /tmp/elan.tar.gz' | sha256sum --check --status \
 && tar -xzf /tmp/elan.tar.gz -C /tmp \
 && ELAN_HOME=/opt/elan-cli /tmp/elan-init -y --no-modify-path --default-toolchain none \
 && rm -f /tmp/elan.tar.gz /tmp/elan-init
COPY . /opt/submission
ENV PATH="/opt/elan-cli/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
WORKDIR /opt/submission
CMD ["bash"]
