# Use Python 3.11 base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install Poetry using the official installation script
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy the pyproject.toml and poetry.lock files
COPY pyproject.toml poetry.lock ./

# Install dependencies via Poetry (including pandas)
RUN poetry config virtualenvs.create false && poetry install --no-dev

# Copy the rest of the application code
COPY . .

# Expose port 80
EXPOSE 80

# Define environment variable (optional)
ENV FLOWBEE_ENV=production

# Command to run the application
CMD ["python", "improved.py"]
