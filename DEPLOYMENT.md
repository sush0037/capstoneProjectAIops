# Healthcare Claim Review Assistant — Setup & Deployment Guide

---

## Table of Contents

1. [Local Setup (Windows)](#1-local-setup-windows)
2. [Local Setup (Mac / Linux)](#2-local-setup-mac--linux)
3. [Deploy on AWS — EC2 with Docker (Recommended for Teams)](#3-deploy-on-aws--ec2-with-docker)
4. [Deploy on AWS — ECS Fargate (Production / Auto-scaling)](#4-deploy-on-aws--ecs-fargate)
5. [Enable S3 Storage for Claim Results](#5-enable-s3-storage-for-claim-results)
6. [Environment Variables Reference](#6-environment-variables-reference)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Local Setup (Windows)

### Prerequisites
- Python 3.10 or higher — https://www.python.org/downloads/
- An OpenAI API key — https://platform.openai.com/api-keys

### Steps

**Step 1 — Clone or download the project**
```
cd C:\Users\<YourName>
git clone <repo-url> healthcare-claim-assistant
cd healthcare-claim-assistant
```

**Step 2 — Create your `.env` file**
```
copy .env.example .env
notepad .env
```
Set your key:
```
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4o-mini
```
Save and close.

**Step 3 — Install Python dependencies**
```
pip install -r requirements.txt
```

**Step 4 — Generate synthetic claim and policy data**
```
python scripts\generate_synthetic_data.py
```
This creates 10 sample claim PDFs and 3 policy documents under `data/`.

**Step 5 — Ingest policy documents into ChromaDB (RAG)**
```
python scripts\ingest_documents.py
```
This embeds the policy documents using OpenAI and stores them locally in `data/chroma_db/`.

**Step 6 — Launch the app**
```
streamlit run app.py
```
Open **http://localhost:8501** in your browser.

> **One-command shortcut:** run `setup.bat` — it performs steps 2–6 automatically and pauses for you to fill in the API key.

---

## 2. Local Setup (Mac / Linux)

Same as above but use forward slashes and `cp` instead of `copy`:

```bash
cp .env.example .env
nano .env          # or: open -e .env  (Mac)

pip install -r requirements.txt
python scripts/generate_synthetic_data.py
python scripts/ingest_documents.py
streamlit run app.py
```
Or just run:
```bash
bash setup.sh
```

---

## 3. Deploy on AWS — EC2 with Docker

This is the simplest way to make the app accessible to your whole team via a public URL.

### What you need
- An AWS account
- AWS CLI installed and configured (`aws configure`)
- Docker installed on your local machine

---

### Step 1 — Launch an EC2 instance

1. Go to **AWS Console → EC2 → Launch Instance**
2. Choose: **Ubuntu Server 22.04 LTS (64-bit)**
3. Instance type: **t3.medium** (2 vCPU, 4 GB RAM — minimum recommended)
4. Key pair: create or select an existing `.pem` key
5. Security group — add these inbound rules:

   | Type  | Port | Source    |
   |-------|------|-----------|
   | SSH   | 22   | Your IP   |
   | HTTP  | 80   | 0.0.0.0/0 |
   | Custom TCP | 8501 | 0.0.0.0/0 |

6. Storage: **20 GB** minimum
7. Click **Launch Instance**

---

### Step 2 — SSH into the instance

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

---

### Step 3 — Install Docker on the EC2 instance

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu
newgrp docker   # apply group change without logout
```

---

### Step 4 — Copy your project to EC2

From your **local machine**:
```bash
scp -i your-key.pem -r C:\Users\Sushil\healthcare-claim-assistant ubuntu@<EC2-PUBLIC-IP>:~/healthcare-claim-assistant
```

Or on the EC2 instance, clone from Git:
```bash
git clone <repo-url> healthcare-claim-assistant
cd healthcare-claim-assistant
```

---

### Step 5 — Create the `.env` file on EC2

```bash
cd ~/healthcare-claim-assistant
cp .env.example .env
nano .env
```
Add your `OPENAI_API_KEY` and save.

---

### Step 6 — Generate data and build the container

```bash
# Install Python to run the one-time data generation scripts
sudo apt-get install -y python3 python3-pip
pip3 install reportlab pdfplumber python-dotenv

python3 scripts/generate_synthetic_data.py
python3 -c "
import os; os.environ['OPENAI_API_KEY'] = open('.env').read().split('OPENAI_API_KEY=')[1].split()[0]
" && pip3 install -r requirements.txt && python3 scripts/ingest_documents.py
```

> **Shortcut:** Run both scripts inside the container after it starts (see Step 7).

---

### Step 7 — Start the app with Docker Compose

```bash
cd ~/healthcare-claim-assistant
docker-compose up -d --build
```

Check it's running:
```bash
docker-compose ps
docker-compose logs -f   # watch live logs
```

The app is now available at:
```
http://<EC2-PUBLIC-IP>:8501
```

Share this URL with your team. No further setup needed on their end — they just open the URL in a browser.

---

### Step 8 — Run data generation inside the container (if skipped above)

```bash
docker-compose exec app python scripts/generate_synthetic_data.py
docker-compose exec app python scripts/ingest_documents.py
```

---

### Keeping the app running after reboot

Docker Compose `restart: unless-stopped` (already set in `docker-compose.yml`) ensures the container auto-restarts. To also start Docker on boot:
```bash
sudo systemctl enable docker
```

---

### Optional — Use a domain name (e.g. claims.yourcompany.com)

1. Point your domain's DNS A-record to the EC2 public IP.
2. Install Nginx as a reverse proxy:
   ```bash
   sudo apt-get install -y nginx
   ```
3. Create `/etc/nginx/sites-available/claims`:
   ```nginx
   server {
       listen 80;
       server_name claims.yourcompany.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
       }
   }
   ```
4. Enable it:
   ```bash
   sudo ln -s /etc/nginx/sites-available/claims /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
5. Add HTTPS with Let's Encrypt (free SSL):
   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d claims.yourcompany.com
   ```

---

## 4. Deploy on AWS — ECS Fargate

Use this when you need auto-scaling, no server management, and production reliability.

### Step 1 — Push Docker image to ECR

```bash
# Authenticate Docker with AWS ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name healthcare-claim-assistant --region us-east-1

# Build and push
docker build -t healthcare-claim-assistant .
docker tag healthcare-claim-assistant:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/healthcare-claim-assistant:latest
docker push \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/healthcare-claim-assistant:latest
```

Replace `<ACCOUNT_ID>` with your 12-digit AWS account ID.

---

### Step 2 — Store secrets in AWS Secrets Manager

Instead of a `.env` file, store your API key securely:

```bash
aws secretsmanager create-secret \
  --name healthcare-claim-assistant/prod \
  --secret-string '{"OPENAI_API_KEY":"sk-...your-key...","OPENAI_MODEL":"gpt-4o-mini"}'
```

---

### Step 3 — Create an ECS Cluster

```bash
aws ecs create-cluster --cluster-name healthcare-claims --region us-east-1
```

---

### Step 4 — Create an ECS Task Definition

Save this as `ecs-task-def.json` (replace placeholders):

```json
{
  "family": "healthcare-claim-assistant",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/healthcare-claim-assistant:latest",
      "portMappings": [{ "containerPort": 8501, "protocol": "tcp" }],
      "secrets": [
        { "name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:healthcare-claim-assistant/prod:OPENAI_API_KEY::" },
        { "name": "OPENAI_MODEL",   "valueFrom": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:healthcare-claim-assistant/prod:OPENAI_MODEL::" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/healthcare-claim-assistant",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register it:
```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-def.json
```

---

### Step 5 — Create an ECS Service with a Load Balancer

1. **AWS Console → EC2 → Load Balancers → Create Application Load Balancer**
   - Scheme: Internet-facing
   - Port 80 (HTTP) listener → forward to target group on port 8501
   - Security group: allow 80/443 from 0.0.0.0/0

2. **AWS Console → ECS → Clusters → healthcare-claims → Create Service**
   - Launch type: **Fargate**
   - Task definition: `healthcare-claim-assistant`
   - Desired tasks: `1` (scale up as needed)
   - VPC: your default VPC, public subnets
   - Load balancer: attach the ALB you created
   - Auto-assign public IP: **Enabled**

3. Once the service is running, the app is accessible via the **ALB DNS name**:
   ```
   http://healthcare-claims-alb-<id>.us-east-1.elb.amazonaws.com
   ```

---

## 5. Enable S3 Storage for Claim Results

The app can save reviewed claim PDFs and JSON results to S3 automatically.

### Step 1 — Create an S3 bucket

```bash
aws s3 mb s3://healthcare-claims-bucket --region us-east-1
```

Enable versioning (optional but recommended):
```bash
aws s3api put-bucket-versioning \
  --bucket healthcare-claims-bucket \
  --versioning-configuration Status=Enabled
```

### Step 2 — Add AWS credentials to `.env`

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET_NAME=healthcare-claims-bucket
```

On EC2/ECS, prefer using an **IAM Role** attached to the instance/task instead of hardcoded keys — then leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` blank and boto3 will pick up the role automatically.

### Step 3 — IAM permissions needed

The role / user must have:
```json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::healthcare-claims-bucket",
    "arn:aws:s3:::healthcare-claims-bucket/*"
  ]
}
```

Once configured, every approved or rejected claim will be saved to:
```
s3://healthcare-claims-bucket/claims/<timestamp>_<claim_id>/
    ├── claim.pdf
    └── review_result.json
```

---

## 6. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model (`gpt-4o` for higher accuracy) |
| `AWS_ACCESS_KEY_ID` | No | — | AWS key (leave blank to use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | No | — | AWS secret |
| `AWS_DEFAULT_REGION` | No | `us-east-1` | AWS region |
| `AWS_S3_BUCKET_NAME` | No | `healthcare-claims-bucket` | S3 bucket for saving results |
| `CHROMA_PERSIST_DIR` | No | `./data/chroma_db` | Local path for ChromaDB vector store |
| `POLICY_DOCS_DIR` | No | `./data/policy_documents` | Path to policy PDFs |
| `CLAIMS_DIR` | No | `./data/synthetic_claims` | Path to sample claim PDFs |
| `OUTPUT_DIR` | No | `./data/outputs` | Local path for saved results |

---

## 7. Troubleshooting

### `PermissionDeniedError: model not found` (embedding model)
The default `text-embedding-ada-002` is deprecated on newer project keys.
**Fix:** Already patched in `src/rag/ingestion.py` to use `text-embedding-3-small`.

### `streamlit: email prompt appears`
**Fix:** Create `~/.streamlit/credentials.toml` (done automatically on Windows by this setup):
```toml
[general]
email = ""
```

### ChromaDB already has data / stale embeddings
Force a clean re-ingest:
```bash
python scripts/ingest_documents.py --force
```

### Docker container exits immediately
Check logs:
```bash
docker-compose logs app
```
Most common cause: missing or invalid `OPENAI_API_KEY` in `.env`.

### EC2 port 8501 not reachable
Verify the Security Group inbound rule allows TCP 8501 from `0.0.0.0/0`.

### `pip install` fails on Windows with build errors
Install the Visual C++ Build Tools:
https://visualstudio.microsoft.com/visual-cpp-build-tools/
