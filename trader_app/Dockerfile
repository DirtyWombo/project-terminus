FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the service-specific requirements file
COPY trader_app/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . /app

EXPOSE 5000

# Run the application
CMD ["gunicorn", "trader_app.wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "3"]