FROM python:3.12-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /code/uploads /code/app/ml_engine/models

# Copy the core backend application files
COPY ./app /code/app
COPY ./pretrained_models /code/pretrained_models
COPY ./fine_tuned_model /code/fine_tuned_model

# Expose the standard HF Spaces port
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
