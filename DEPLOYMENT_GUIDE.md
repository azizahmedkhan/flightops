# AeroOps Cloud Deployment Guide

Deploy AeroOps to the internet using one of these cloud platforms.

---

## 🚀 Option 1: Deploy to Render.com (Easiest - Recommended)

**Time:** 15-20 minutes  
**Cost:** ~$25/month for starter tier  
**Best for:** Quick demos, MVP, small production deployments

### Steps:

1. **Sign up at [render.com](https://render.com)**

2. **Connect your GitHub repository**
   - Push this code to GitHub
   - In Render dashboard, click "New" → "Blueprint"
   - Connect your repository
   - Render will auto-detect `render.yaml`

3. **Set environment variables**
   - In Render dashboard, go to each service
   - Add your `OPENAI_API_KEY` as an environment variable
   - Other variables are auto-configured from `render.yaml`

4. **Deploy!**
   - Click "Apply" to deploy all services
   - Wait 10-15 minutes for initial build
   - Your app will be live at: `https://web-XXXX.onrender.com`

5. **Seed the database**
   ```bash
   curl -X POST https://gateway-api-XXXX.onrender.com/ingest/seed
   ```

### Render Advantages:
- ✅ Free PostgreSQL with pgvector support
- ✅ Automatic SSL certificates
- ✅ Auto-deploys on git push
- ✅ Built-in monitoring
- ✅ Easy rollbacks

---

## 🔥 Option 2: Deploy to Fly.io (Budget-Friendly)

**Time:** 20 minutes  
**Cost:** ~$15-20/month  
**Best for:** Cost-conscious deployments, global edge deployment

### Steps:

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and create apps**
   ```bash
   fly auth login
   cd /Users/aziz/work/flightops
   ```

3. **Create deployment script**
   Run this script to create all Fly apps:

   ```bash
   #!/bin/bash
   # Save as: deploy-fly.sh
   
   # Create Postgres database
   fly postgres create --name flightops-db --region sjc --vm-size shared-cpu-1x --volume-size 10
   
   # Attach to apps
   fly postgres attach --app flightops-gateway flightops-db
   
   # Create Redis
   fly redis create --name flightops-redis --region sjc
   
   # Deploy services
   cd services/gateway-api && fly launch --name flightops-gateway --region sjc
   cd ../knowledge-engine && fly launch --name flightops-knowledge --region sjc
   cd ../agent-svc && fly launch --name flightops-agent --region sjc
   cd ../comms-svc && fly launch --name flightops-comms --region sjc
   cd ../../ui/web && fly launch --name flightops-web --region sjc
   
   echo "✅ Deployment complete!"
   echo "🌐 Your app: https://flightops-web.fly.dev"
   ```

4. **Set secrets**
   ```bash
   fly secrets set OPENAI_API_KEY=your_key_here --app flightops-gateway
   fly secrets set OPENAI_API_KEY=your_key_here --app flightops-knowledge
   fly secrets set OPENAI_API_KEY=your_key_here --app flightops-agent
   ```

---

## ☁️ Option 3: Deploy to AWS (Production-Grade)

**Time:** 45-60 minutes  
**Cost:** ~$100-200/month  
**Best for:** Enterprise production, high availability, compliance requirements

### Architecture: AWS ECS Fargate + RDS + ALB

1. **Prerequisites**
   ```bash
   # Install AWS CLI
   brew install awscli
   aws configure
   
   # Install ECS CLI
   brew install amazon-ecs-cli
   ```

2. **Create AWS deployment script**
   Save this as `deploy-aws.sh`:

   ```bash
   #!/bin/bash
   set -e
   
   REGION="us-east-1"
   CLUSTER_NAME="flightops-cluster"
   ECR_REPO="flightops"
   
   echo "🚀 Deploying AeroOps to AWS..."
   
   # 1. Create ECR repository
   aws ecr create-repository --repository-name $ECR_REPO --region $REGION || true
   
   # 2. Get ECR login
   aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com
   
   # 3. Build and push images
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ECR_BASE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"
   
   docker compose -f infra/docker-compose.yml build
   
   # Tag and push each service
   for service in gateway-api knowledge-engine agent-svc comms-svc ingest-svc web; do
     docker tag infra-$service:latest $ECR_BASE:$service-latest
     docker push $ECR_BASE:$service-latest
   done
   
   # 4. Create RDS PostgreSQL with pgvector
   aws rds create-db-instance \
     --db-instance-identifier flightops-db \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --engine-version 16.1 \
     --master-username postgres \
     --master-user-password ChangeThisPassword123! \
     --allocated-storage 20 \
     --region $REGION \
     --publicly-accessible \
     --backup-retention-period 7 || echo "RDS already exists"
   
   # 5. Create ECS cluster
   aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION || true
   
   # 6. Create task definitions and services
   # (See detailed task-definition.json below)
   
   echo "✅ Deployment initiated!"
   echo "🔗 Check AWS Console for load balancer URL"
   ```

3. **Create ECS Task Definition**
   Save as `aws-task-definition.json`:

   ```json
   {
     "family": "flightops",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "containerDefinitions": [
       {
         "name": "gateway-api",
         "image": "YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/flightops:gateway-api-latest",
         "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
         "environment": [
           {"name": "DB_HOST", "value": "YOUR_RDS_ENDPOINT"},
           {"name": "DB_NAME", "value": "flightops"},
           {"name": "DB_USER", "value": "postgres"}
         ],
         "secrets": [
           {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:flightops/openai"},
           {"name": "DB_PASS", "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:flightops/dbpass"}
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/flightops",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

4. **Deploy with CLI**
   ```bash
   chmod +x deploy-aws.sh
   ./deploy-aws.sh
   ```

---

## 🐳 Option 4: Deploy to DigitalOcean (Balanced)

**Time:** 30 minutes  
**Cost:** ~$50-80/month  
**Best for:** Kubernetes experience, good balance of cost and features

### Steps:

1. **Install doctl**
   ```bash
   brew install doctl
   doctl auth init
   ```

2. **Create Kubernetes cluster**
   ```bash
   doctl kubernetes cluster create flightops-cluster \
     --region nyc1 \
     --node-pool "name=worker-pool;size=s-2vcpu-4gb;count=2" \
     --auto-upgrade=true
   ```

3. **Create managed database**
   ```bash
   doctl databases create flightops-db \
     --engine pg \
     --version 16 \
     --region nyc1 \
     --size db-s-1vcpu-1gb
   ```

4. **Deploy with Kubernetes**
   ```bash
   # Get kubectl config
   doctl kubernetes cluster kubeconfig save flightops-cluster
   
   # Create secrets
   kubectl create secret generic flightops-secrets \
     --from-literal=OPENAI_API_KEY=your_key_here \
     --from-literal=DB_PASS=your_db_password
   
   # Deploy using existing Kubernetes manifests
   kubectl apply -k infra/bridge/overlays/desktop
   
   # Expose services with LoadBalancer
   kubectl patch service web -p '{"spec":{"type":"LoadBalancer"}}'
   kubectl patch service gateway-api -p '{"spec":{"type":"LoadBalancer"}}'
   
   # Get public IPs
   kubectl get services
   ```

5. **Get your public URL**
   ```bash
   kubectl get svc web -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
   ```

---

## 🔐 Post-Deployment Checklist

After deploying to any platform:

### 1. Secure your environment variables
- [ ] Set strong `DB_PASS`
- [ ] Add `OPENAI_API_KEY`
- [ ] Set `ALLOW_UNGROUNDED_ANSWERS=false` for production

### 2. Initialize the database
```bash
# Replace with your gateway URL
curl -X POST https://your-gateway-url.com/ingest/seed
```

### 3. Set up custom domain (optional)
- Point your domain to the load balancer IP/URL
- Configure SSL/TLS (most platforms provide free SSL)

### 4. Enable monitoring
- [ ] Set up application logging
- [ ] Enable error tracking (Sentry, etc.)
- [ ] Configure Prometheus metrics scraping

### 5. Set up backups
- [ ] Enable database backups
- [ ] Configure backup retention policy

---

## 💰 Cost Comparison

| Platform | Monthly Cost | Setup Time | Best For |
|----------|-------------|------------|----------|
| **Render** | $25-40 | 15 min | Quick demos, MVPs |
| **Fly.io** | $15-25 | 20 min | Budget deployments |
| **Railway** | $20-35 | 10 min | Simplest setup |
| **DigitalOcean** | $50-80 | 30 min | Kubernetes learning |
| **AWS ECS** | $100-200 | 60 min | Enterprise production |
| **AWS EKS** | $150-300 | 90 min | Large scale |

---

## 🆘 Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs -f

# Or on cloud platform
kubectl logs -l app=gateway-api
```

### Database connection issues
- Verify `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS` are correct
- Check firewall rules allow connections
- Ensure pgvector extension is installed

### OpenAI API errors
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota/billing

### WebSocket issues (for scalable-chatbot-svc)
- Ensure load balancer supports WebSocket upgrades
- Check timeout settings (should be > 60 seconds)

---

## 📚 Next Steps

Once deployed:
1. Visit your app URL
2. Test the demo scenarios
3. Set up monitoring dashboards
4. Configure CI/CD for auto-deploys
5. Add your custom domain

**Need help?** Open an issue in the repository.
