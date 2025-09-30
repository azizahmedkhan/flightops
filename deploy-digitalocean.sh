#!/bin/bash
# FlightOps - DigitalOcean Deployment Script
# This script deploys FlightOps to DigitalOcean Kubernetes

set -e

echo "🚀 Deploying FlightOps to DigitalOcean..."

# Configuration
CLUSTER_NAME="flightops-cluster"
REGION="nyc1"
NODE_SIZE="s-2vcpu-4gb"
NODE_COUNT=2
DB_NAME="flightops-db"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl is not installed. Install it with:"
    echo "   brew install doctl"
    echo "   doctl auth init"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Install it with:"
    echo "   brew install kubectl"
    exit 1
fi

echo -e "${YELLOW}Step 1/6: Creating Kubernetes cluster...${NC}"
doctl kubernetes cluster create $CLUSTER_NAME \
  --region $REGION \
  --node-pool "name=worker-pool;size=$NODE_SIZE;count=$NODE_COUNT" \
  --auto-upgrade=true \
  --wait || echo "Cluster already exists"

echo -e "${YELLOW}Step 2/6: Configuring kubectl...${NC}"
doctl kubernetes cluster kubeconfig save $CLUSTER_NAME

echo -e "${YELLOW}Step 3/6: Creating managed PostgreSQL database...${NC}"
doctl databases create $DB_NAME \
  --engine pg \
  --version 16 \
  --region $REGION \
  --size db-s-1vcpu-1gb || echo "Database already exists"

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 30

# Get database connection details
DB_HOST=$(doctl databases connection $DB_NAME --format Host --no-header)
DB_PORT=$(doctl databases connection $DB_NAME --format Port --no-header)
DB_USER=$(doctl databases connection $DB_NAME --format User --no-header)
DB_PASS=$(doctl databases connection $DB_NAME --format Password --no-header)

echo -e "${YELLOW}Step 4/6: Creating Kubernetes secrets...${NC}"
echo "⚠️  Please enter your OpenAI API key:"
read -s OPENAI_KEY

kubectl create namespace flightops || echo "Namespace already exists"

kubectl create secret generic flightops-secrets -n flightops \
  --from-literal=OPENAI_API_KEY=$OPENAI_KEY \
  --from-literal=DB_HOST=$DB_HOST \
  --from-literal=DB_PORT=$DB_PORT \
  --from-literal=DB_USER=$DB_USER \
  --from-literal=DB_PASS=$DB_PASS \
  --from-literal=DB_NAME=defaultdb \
  --dry-run=client -o yaml | kubectl apply -f -

echo -e "${YELLOW}Step 5/6: Building and pushing Docker images...${NC}"

# Create container registry
doctl registry create flightops-registry || echo "Registry already exists"

# Login to registry
doctl registry login

# Get registry URL
REGISTRY_URL=$(doctl registry get --format Endpoint --no-header)

# Build and push images
echo "Building images..."
cd infra
docker compose build

# Tag and push each service
for service in gateway-api knowledge-engine agent-svc comms-svc ingest-svc customer-chat-svc predictive-svc crew-svc scalable-chatbot-svc db-router-svc; do
  echo "Pushing $service..."
  docker tag infra-$service:latest $REGISTRY_URL/flightops-$service:latest
  docker push $REGISTRY_URL/flightops-$service:latest
done

# Push web
docker tag infra-web:latest $REGISTRY_URL/flightops-web:latest
docker push $REGISTRY_URL/flightops-web:latest

cd ..

echo -e "${YELLOW}Step 6/6: Deploying to Kubernetes...${NC}"

# Create deployment manifests with updated image URLs
cat > k8s-deployment.yaml <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: flightops
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway-api
  namespace: flightops
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway-api
  template:
    metadata:
      labels:
        app: gateway-api
    spec:
      containers:
      - name: gateway-api
        image: $REGISTRY_URL/flightops-gateway-api:latest
        ports:
        - containerPort: 8080
        env:
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: flightops-secrets
              key: DB_HOST
        - name: DB_PORT
          valueFrom:
            secretKeyRef:
              name: flightops-secrets
              key: DB_PORT
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: flightops-secrets
              key: DB_USER
        - name: DB_PASS
          valueFrom:
            secretKeyRef:
              name: flightops-secrets
              key: DB_PASS
        - name: DB_NAME
          valueFrom:
            secretKeyRef:
              name: flightops-secrets
              key: DB_NAME
        - name: AGENT_URL
          value: "http://agent-svc:8082"
        - name: KNOWLEDGE_SERVICE_URL
          value: "http://knowledge-engine:8081"
        - name: COMMS_URL
          value: "http://comms-svc:8083"
        - name: INGEST_URL
          value: "http://ingest-svc:8084"
---
apiVersion: v1
kind: Service
metadata:
  name: gateway-api
  namespace: flightops
spec:
  type: LoadBalancer
  selector:
    app: gateway-api
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: flightops
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: $REGISTRY_URL/flightops-web:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_GATEWAY_URL
          value: "http://gateway-api"
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: flightops
spec:
  type: LoadBalancer
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 3000
EOF

kubectl apply -f k8s-deployment.yaml

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Waiting for LoadBalancer IPs to be assigned..."
sleep 20

WEB_IP=$(kubectl get svc web -n flightops -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
GATEWAY_IP=$(kubectl get svc gateway-api -n flightops -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 FlightOps is now live on the internet!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "🌐 Web UI: http://$WEB_IP"
echo "🔗 Gateway API: http://$GATEWAY_IP"
echo "📊 API Docs: http://$GATEWAY_IP/docs"
echo ""
echo "Next steps:"
echo "1. Seed the database:"
echo "   curl -X POST http://$GATEWAY_IP/ingest/seed"
echo ""
echo "2. Set up a custom domain (optional):"
echo "   Point your domain A record to: $WEB_IP"
echo ""
echo "3. View logs:"
echo "   kubectl logs -n flightops -l app=gateway-api -f"
echo ""
echo "4. Scale services:"
echo "   kubectl scale deployment gateway-api -n flightops --replicas=3"
echo ""
echo -e "${YELLOW}⚠️  Note: It may take a few minutes for all services to be ready${NC}"
