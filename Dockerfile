FROM python:3.11-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY models/ ./models/
ENV HF_HOME=/srv/models \
    TRANSFORMERS_OFFLINE=1 \
    SENTENCE_TRANSFORMERS_HOME=/srv/models

COPY app ./app
COPY .env .env
COPY docs /srv/docs

# Faster uvicorn worker class (“uvicorn[standard]” is in requirements)
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]