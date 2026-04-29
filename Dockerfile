FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the standard Cloud Run port
EXPOSE 8000

# The dynamic startup command for Cloud Run
CMD ["python", "-m", "chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000", "--headless"]