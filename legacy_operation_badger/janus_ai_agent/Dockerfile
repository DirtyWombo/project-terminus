# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the service-specific requirements file and install dependencies
# (Ensure you have a requirements.txt inside your janus_ai_agent folder)
COPY janus_ai_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project to create the correct file structure
COPY . /app

# Define the command to run the application with the correct path
CMD ["python", "janus_ai_agent/agent.py"]