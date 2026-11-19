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
#
# SQLite persistence note:
#   Code Engine containers are stateless. The SQLite DB is seeded fresh on
#   every cold start via start.sh → seed_academic.py (idempotent).
#   User uploads and generated content are lost on restart.
#   For persistent storage, set DATABASE_URL to a PostgreSQL connection string.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all required application files
COPY app/ app/
COPY data/ data/
COPY migrations/ migrations/
COPY run.py .
COPY seed_academic.py .
COPY start.sh .

# Create uploads directory and make start.sh executable
RUN mkdir -p uploads && chmod +x start.sh

# Code Engine uses PORT env var; default 8080 matches CE convention
ENV PORT=8080

EXPOSE 8080

# start.sh: seeds CS201 dataset (idempotent), then launches Gunicorn
CMD ["./start.sh"]
