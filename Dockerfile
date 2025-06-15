FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ ./scripts/
COPY model/ ./model/
COPY input/ ./input/
COPY output/ ./output/

# Create templates directory for web app
RUN mkdir -p scripts/templates

ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/kafka_scoring_service.py"] 