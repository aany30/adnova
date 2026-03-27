FROM python:3.11-slim

# Install system dependencies for OpenCV and general media processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements from the backend folder
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual backend code into the container
COPY backend/ .

# Railway provides the PORT environment variable
ENV PORT 8080
EXPOSE 8080

# Run uvicorn using the provided PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
