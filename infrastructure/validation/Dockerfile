FROM ubuntu:22.04

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install base tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    python3.10 \
    python3-pip \
    nodejs \
    npm \
    bash \
    timeout \
    coreutils \
    && rm -rf /var/lib/apt/lists/*

# Install Python tools
RUN pip3 install --no-cache-dir \
    pytest \
    flake8 \
    mypy \
    pylint

# Install Node tools globally
RUN npm install -g eslint typescript

# Disable network by default (override with --network=host if needed)
ENV NO_PROXY=localhost,127.0.0.1
ENV no_proxy=localhost,127.0.0.1

# Set working directory
WORKDIR /workspace

# Copy validation scripts
COPY infrastructure/validation/validate_patch.sh /usr/local/bin/validate_patch.sh
COPY infrastructure/validation/report_confidence.py /usr/local/bin/report_confidence.py

RUN chmod +x /usr/local/bin/validate_patch.sh
RUN chmod +x /usr/local/bin/report_confidence.py

# Resource limits
RUN ulimit -t 300 -v 2097152

CMD ["/bin/bash"]
