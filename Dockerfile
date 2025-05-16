FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Expose the port the app runs on
EXPOSE 8002

# Command to run the application
CMD ["python", "server.py"]
