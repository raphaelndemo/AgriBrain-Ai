FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your Python scripts, folders, and ML models into the container
COPY . .

# Open port 7860 so internet traffic can reach the app
EXPOSE 7860

# The command Google Cloud to start app
CMD ["python", "-m", "chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "7860", "--headless"]