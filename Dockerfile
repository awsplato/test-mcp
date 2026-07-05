# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install uv for fast dependency resolution and installation
RUN pip install --no-cache-dir uv

# Copy just the dependency file first to leverage Docker cache
COPY pyproject.toml ./

# Install dependencies globally inside the container using uv
RUN uv pip compile pyproject.toml -o requirements.txt && \
    uv pip install --system -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 3000 to the outside world
EXPOSE 3000

# Run the FastMCP server
CMD ["python", "main.py"]
