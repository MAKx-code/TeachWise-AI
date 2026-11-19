# TeachWise AI — IBM Cloud Code Engine Deployment
#
# Build and push:
#   docker build -t teachwise-ai .
#   docker tag teachwise-ai us.icr.io/<namespace>/teachwise-ai:latest
#   docker push us.icr.io/<namespace>/teachwise-ai:latest
#
# Deploy on Code Engine:
#   ibmcloud ce application create \
#     --name teachwise-ai \
#     --image us.icr.io/<namespace>/teachwise-ai:latest \
#     --port 8080 \
#     --env WATSONX_API_KEY=<key> \
#     --env WATSONX_PROJECT_ID=<id> \
#     --env WATSONX_URL=https://us-south.ml.cloud.ibm.com \
#     --env WATSONX_MODEL_ID=ibm/granite-3-8b-instruct \
#     --env SECRET_KEY=<random-secret> \
#     --env DATABASE_URL=sqlite:///teachwise.db

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (never copy .env)
COPY app/ app/
COPY data/ data/
COPY run.py .

# Create uploads directory
RUN mkdir -p uploads

# Code Engine uses PORT env var; default 8080 matches CE convention
ENV PORT=8080

EXPOSE 8080

# Use Gunicorn for production; 2 workers, 120s timeout for Granite calls
CMD gunicorn run:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120
