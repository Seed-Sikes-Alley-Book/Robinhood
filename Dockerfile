# Use a small, secure base image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Install system dependencies (needed for numpy, scipy, lxml, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt 

RUN pip install --no-cache-dir \
    yfinance==1.4.1 \
    pandas==2.2.2 \
    numpy==1.24.0 \
    scipy==1.10.0 \
    matplotlib==3.7.0 \
    pyarrow==12.0.0 \
    lxml==4.9.0 \
    PyNaCl==1.5.0 \
    python-dotenv==1.0.1 



# Copy project files
COPY . .

# Create non-root user for security
RUN useradd -m appuser
USER appuser

# Default command
CMD ["python", "main.py"]
