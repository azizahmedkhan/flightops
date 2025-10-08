# 🚀 Quick Deploy FlightOps to the Internet

Choose the fastest option for you:

---

## ⚡ **FASTEST: Render.com (15 minutes)**

### One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

### Manual Steps:

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Deploy on Render**
   - Go to https://render.com/
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml` automatically
   - Add your `OPENAI_API_KEY` in the environment variables
   - Click "Apply"

3. **Wait for deployment** (10-15 minutes)

4. **Seed the database**
   ```bash
   # Replace with your gateway URL from Render dashboard
   curl -X POST https://gateway-api-XXXX.onrender.com/ingest/seed
   ```

5. **Access your app**
   - Web UI: `https://web-XXXX.onrender.com`
   - API: `https://gateway-api-XXXX.onrender.com/docs`

**Done! Your app is live on the internet!** 🎉

---

## 🐳 **EASIEST: DigitalOcean App Platform (20 minutes)**

Perfect if you want a simple PaaS experience.

### Steps:

1. **Sign up at [DigitalOcean](https://www.digitalocean.com)**

2. **Create App**
   - Click "Create" → "Apps"
   - Select "GitHub" and connect your repository
   - Select the `flightops` repo

3. **Configure Services**
   - DigitalOcean will auto-detect your Dockerfiles
   - Add these services:
     - `gateway-api` (Dockerfile: `services/gateway-api/Dockerfile`)
     - `web` (Dockerfile: `ui/web/Dockerfile`)
     - `knowledge-engine`, `agent-svc`, `comms-svc`, etc.

4. **Add Database**
   - Click "Add Resource" → "Database"
   - Select PostgreSQL 16
   - Choose "Dev Database" ($12/mo) or "Basic" ($15/mo)

5. **Add Environment Variables**
   ```
   OPENAI_API_KEY=your_key_here
   CHAT_MODEL=gpt-4o-mini
   EMBEDDINGS_MODEL=text-embedding-3-small
   ```

6. **Deploy!**
   - Click "Create Resources"
   - Wait 10-15 minutes
   - Your app will be at: `https://your-app.ondigitalocean.app`

**Cost:** ~$30-50/month

---

## 🌩️ **ADVANCED: DigitalOcean Kubernetes (30 minutes)**

For those who want more control and Kubernetes experience.

### Prerequisites:
```bash
# Install doctl
brew install doctl

# Install kubectl
brew install kubectl

# Authenticate
doctl auth init
```

### Deploy:
```bash
# Make script executable
chmod +x deploy-digitalocean.sh

# Run deployment
./deploy-digitalocean.sh
```

The script will:
1. ✅ Create a Kubernetes cluster ($24/month for 2 nodes)
2. ✅ Create managed PostgreSQL ($15/month)
3. ✅ Build and push Docker images
4. ✅ Deploy all services
5. ✅ Set up LoadBalancers
6. ✅ Give you public URLs

**Total time:** ~30 minutes (mostly waiting for provisioning)

---

## 💻 **LOCAL TEST FIRST (Recommended)**

Before deploying to production, test locally:

```bash
# 1. Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY=your_key_here
CHAT_MODEL=gpt-4o-mini
EMBEDDINGS_MODEL=text-embedding-3-small
DB_HOST=db
DB_PORT=5432
DB_NAME=flightops
DB_USER=postgres
DB_PASS=postgres
ALLOW_UNGROUNDED_ANSWERS=false
EOF

# 2. Start services
cd infra
docker compose up --build

# 3. Seed database (in new terminal)
curl -X POST http://localhost:8084/ingest/seed

# 4. Test app
open http://localhost:3000
```

---

## 🎯 **Which Platform Should I Choose?**

| Platform | Best For | Cost/Month | Setup Time |
|----------|----------|------------|------------|
| **Render** | Quick demos, MVPs | $25-40 | 15 min |
| **DO App Platform** | Simple PaaS | $30-50 | 20 min |
| **DO Kubernetes** | Learning K8s, scalability | $40-80 | 30 min |
| **AWS ECS** | Enterprise, compliance | $100+ | 60 min |
| **Fly.io** | Global edge, low cost | $15-25 | 20 min |

### My Recommendation:
- **For demo/MVP:** Use **Render.com** (easiest, good free tier)
- **For production:** Use **DigitalOcean Kubernetes** (scalable, affordable)
- **For enterprise:** Use **AWS ECS/EKS** (most features, compliance-ready)

---

## 🔧 **Post-Deployment Checklist**

After your app is live:

- [ ] Test all endpoints: `/docs` on gateway-api
- [ ] Seed the database: `curl -X POST <gateway-url>/ingest/seed`
- [ ] Test a flight query in the UI
- [ ] Set up monitoring/alerts
- [ ] Configure custom domain (optional)
- [ ] Enable HTTPS/SSL (most platforms do this automatically)
- [ ] Set up database backups
- [ ] Configure CI/CD for auto-deploys

---

## 🆘 **Need Help?**

### Common Issues:

**Services won't connect:**
- Check internal DNS/networking
- Verify environment variables are set correctly

**Database connection fails:**
- Ensure pgvector extension is installed
- Check firewall rules

**OpenAI API errors:**
- Verify API key is correct
- Check billing/quota

**Logs:**
```bash
# Render
Check dashboard logs

# DigitalOcean K8s
kubectl logs -n flightops -l app=gateway-api

# Docker Compose
docker compose logs -f gateway-api
```

---

## 🎉 **You're All Set!**

Your FlightOps app is now live on the internet and ready to handle irregular operations for airlines worldwide!

**What's Next?**
1. Share your demo URL
2. Test with real scenarios
3. Customize for your use case
4. Scale as needed

Good luck! 🚀





