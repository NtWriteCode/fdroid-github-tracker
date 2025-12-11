FROM python:3.14-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jdk-headless \
    apksigner \
    curl \
    git \
    && pip install --no-cache-dir fdroidserver pyyaml \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Java Home
ENV JAVA_HOME="/usr/lib/jvm/default-java"

# Create app directory
WORKDIR /app

# Copy update script
COPY update_fdroid.py /app/update_fdroid.py
RUN chmod +x /app/update_fdroid.py

# Run Python script directly (handles its own looping)
CMD ["python3", "-u", "/app/update_fdroid.py"]
