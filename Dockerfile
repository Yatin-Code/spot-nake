# Use a lightweight Python base
FROM python:3.11-slim

# Create the standard HuggingFace user
RUN useradd -m -u 1000 user
ENV PATH="/home/user/.local/bin:$PATH"

# Install system dependencies (ffmpeg is required for yt-dlp & mutagen)
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    mkdir -p /data/downloads && \
    chown -R user:user /data && \
    rm -rf /var/lib/apt/lists/*

# Switch to the non-root user for security and HF compliance
USER user
WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY --chown=user:user requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user:user . /app/

# Ensure the download directory exists and has permissions
RUN mkdir -p /app/data/downloads

# Expose the aiohttp health check port
EXPOSE 7860

# Execute the application
CMD ["python", "-m", "bot.main"]
