# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Add labels for container metadata
LABEL org.opencontainers.image.title="AudiobookBay Automated"
LABEL org.opencontainers.image.description="A lightweight web application for searching AudiobookBay and sending magnet links to torrent clients"
LABEL org.opencontainers.image.source="https://github.com/zprough/audiobookbay-automated"
LABEL org.opencontainers.image.licenses="MIT"

# Set the working directory in the container
WORKDIR /app

# Copy the app directory contents into the container
COPY /app /app

# Install any necessary dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose the port the app runs on
EXPOSE 5078

# Define the command to run the application
CMD ["python", "app.py"]
