# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
# This will copy rofl_evaluator.py and any other files in rofl_app/
COPY . /app/

# Install any needed packages specified in requirements.txt
# For rofl_evaluator.py, we only use built-in 'json', 'argparse', 'logging'
# If you add dependencies later (e.g., 'requests' for actual Fitbit API),
# create a requirements.txt and uncomment the next line:
# RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container (if needed for a web service, not for this script)
# EXPOSE 80 

# Define environment variable
# ENV NAME World

# Run rofl_evaluator.py when the container launches
# The actual command with arguments will be provided by the ROFL runtime (compose.yaml)
# This ENTRYPOINT just specifies the base command.
ENTRYPOINT ["python", "rofl_evaluator.py"] 