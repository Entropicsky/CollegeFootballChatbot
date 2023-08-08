# Use a lightweight Python runtime as a parent image
FROM python:3.11.3-slim

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
COPY . .

# Install GDAL dependencies, g++ for Fiona, and clean up
RUN apt-get update \
    && apt-get install -y libgdal-dev g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install any needed packages specified in requirements.txt and gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Use gunicorn and grab the port from environment variable
CMD gunicorn main:app -b 0.0.0.0:$PORT