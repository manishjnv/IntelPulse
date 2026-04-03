# IntelPulse AWS Bedrock Demo

**Simplified demo for AWS Codethon** - Running IntelPulse on EC2 with direct Bedrock SDK integration.

## What This Demo Shows

✅ **Amazon Bedrock Integration** - Direct SDK calls to Claude 3.5 Sonnet  
✅ **Threat Intelligence Analysis** - AI-powered IOC analysis  
✅ **Simple API Endpoint** - Input → Bedrock → Structured Output  
✅ **Production-Ready Code** - FastAPI, Docker, PostgreSQL  
✅ **Minimal Infrastructure** - Single EC2 instance, no complex setup  

## Architecture

```
┌─────────────┐
│   Client    │
│  (Browser/  │
│    curl)    │
└──────┬──────┘
       │ HTTP POST
       │ /api/v1/demo/analyze
       ▼
┌─────────────────────────────────────┐
│         EC2 Instance                │
│  ┌─────────────────────────────┐   │
│  │  FastAPI Application        │   │
│  │  (Docker Container)         │   │
│  │                             │   │
│  │  ┌──────────────────────┐   │   │
│  │  │ Bedrock Adapter      │   │   │
│  │  │ (boto3 SDK)          │   │   │
│  │  └──────────┬───────────┘   │   │
│  └─────────────┼───────────────┘   │
│                │                    │
│                │ AWS SDK Call       │
│                ▼                    │
│  ┌─────────────────────────────┐   │
│  │  IAM Role                   │   │
│  │  (Bedrock Permissions)      │   │
│  └─────────────┬───────────────┘   │
└────────────────┼───────────────────┘
                 │
                 │ bedrock:InvokeModel
                 ▼
        ┌────────────────────┐
        │  Amazon Bedrock    │
        │  Claude 3.5 Sonnet │
        └────────────────────┘
```

## Quick Start

### 1. Prerequisites

- AWS Account with Bedrock access
- EC2 instance (t3.medium or larger)
- IAM role with Bedrock permissions attached to EC2

### 2. Setup (5 minutes)

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Clone repo
git clone https://github.com/YOUR_USERNAME/ti-platform.git
cd ti-platform

# Create environment file
cat > .env <<EOF
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)
AWS_REGION=us-east-1
AI_API_URL=bedrock
AI_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
DEV_BYPASS_AUTH=true
EOF

# Start services
docker-compose -f docker-compose.demo.yml up -d
```

### 3. Test (1 minute)

```bash
# Health check
curl http://localhost:8000/api/v1/demo/health

# Analyze a threat
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-domain.com",
    "ioc_type": "domain"
  }' | jq
```

### 4. View API Docs

Open in browser: `http://YOUR_EC2_IP:8000/api/docs`

## API Endpoint

### POST /api/v1/demo/analyze

Analyze an Indicator of Compromise using Amazon Bedrock.

**Request:**

```json
{
  "ioc": "192.168.1.100",
  "ioc_type": "ip"
}
```

**Response:**

```json
{
  "ioc": "192.168.1.100",
  "ioc_type": "ip",
  "analysis": "Full AI-generated analysis text...",
  "risk_score": 75,
  "severity": "HIGH",
  "confidence": 85,
  "mitre_techniques": ["T1566", "T1059"],
  "recommended_actions": [
    "Block IP at firewall",
    "Review logs for connections",
    "Alert security team"
  ]
}
```

**Supported IOC Types:**

- `ip` - IP addresses
- `domain` - Domain names
- `hash` - File hashes (MD5, SHA1, SHA256)

## Demo Script

### For Live Presentation

**1. Show the infrastructure:**

```bash
# SSH to EC2
ssh ubuntu@$EC2_IP

# Show running containers
docker-compose -f docker-compose.demo.yml ps
```

**2. Open API documentation:**

- Browser: `http://$EC2_IP:8000/api/docs`
- Show the `/api/v1/demo/analyze` endpoint
- Click "Try it out"

**3. Live analysis:**

```bash
# Analyze a suspicious IP
curl -X POST http://$EC2_IP:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "45.142.212.61",
    "ioc_type": "ip"
  }' | jq
```

**4. Explain the flow:**

- Input: IOC (IP, domain, or hash)
- Processing: FastAPI → Bedrock SDK → Claude 3.5 Sonnet
- Output: Structured JSON with risk assessment
- No agents, no complex infrastructure - just direct SDK calls

**5. Show the code:**

```bash
# Show the demo endpoint
cat api/app/routes/demo.py | head -50

# Show Bedrock adapter
cat api/app/services/bedrock_adapter.py | head -50
```

## Key Features Demonstrated

### 1. Amazon Bedrock Integration

- Direct SDK calls using boto3
- Claude 3.5 Sonnet model
- Structured prompt engineering
- Response parsing and validation

### 2. Threat Intelligence Analysis

- IOC risk scoring (0-100)
- Severity classification (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- MITRE ATT&CK technique mapping
- Actionable recommendations

### 3. Production-Ready Code

- FastAPI with async/await
- Pydantic models for validation
- Structured logging
- Error handling
- Health checks

### 4. Minimal Infrastructure

- Single EC2 instance
- Docker Compose for orchestration
- PostgreSQL for data persistence
- Redis for caching
- No OpenSearch, no agents, no complex setup

## Code Highlights

### Bedrock Adapter (`api/app/services/bedrock_adapter.py`)

```python
class BedrockAdapter:
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region,
        )
    
    async def ai_analyze(self, system_prompt: str, user_prompt: str):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "temperature": 0.3,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
        )
        
        return response_body["content"][0]["text"]
```

### Demo Endpoint (`api/app/routes/demo.py`)

```python
@router.post("/analyze")
async def analyze_threat(request: ThreatAnalysisRequest):
    bedrock = get_bedrock_adapter()
    
    system_prompt = "You are a cybersecurity threat analyst..."
    user_prompt = f"Analyze this IOC: {request.ioc}..."
    
    analysis_text = await bedrock.ai_analyze(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    
    return ThreatAnalysisResponse(
        ioc=request.ioc,
        analysis=analysis_text,
        risk_score=extract_risk_score(analysis_text),
        severity=extract_severity(analysis_text),
        ...
    )
```

## Testing

### Automated Tests

```bash
# Install test dependencies
pip install httpx

# Run test suite
python test_bedrock_demo.py
```

### Manual Tests

```bash
# Test IP address
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "1.2.3.4", "ioc_type": "ip"}'

# Test domain
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "evil.com", "ioc_type": "domain"}'

# Test hash
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "44d88612fea8a8f36de82e1278abb02f", "ioc_type": "hash"}'
```

## Troubleshooting

### Bedrock Permission Denied

```bash
# Check IAM role
aws sts get-caller-identity

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### API Not Responding

```bash
# Check logs
docker-compose -f docker-compose.demo.yml logs api

# Restart services
docker-compose -f docker-compose.demo.yml restart
```

### Database Issues

```bash
# Check PostgreSQL
docker-compose -f docker-compose.demo.yml logs postgres

# Connect to database
docker-compose -f docker-compose.demo.yml exec postgres psql -U ti -d ti_platform
```

## Cost Estimate

**EC2 (t3.medium):** ~$1/day  
**Bedrock API calls:** ~$0.01-0.05 per analysis  
**Total demo cost:** ~$10-15

## What's NOT Included (Intentionally)

❌ CDK deployment  
❌ Bedrock agents or action groups  
❌ Multi-agent orchestration  
❌ OpenSearch integration  
❌ Complex infrastructure  
❌ Production authentication  

**Why?** This is a simplified demo focused on showing Bedrock integration working end-to-end.

## Next Steps

After successful demo:

1. **Add Authentication** - Disable `DEV_BYPASS_AUTH`
2. **Add HTTPS** - Use Caddy or ALB with ACM certificate
3. **Scale Infrastructure** - Move to ECS Fargate or EKS
4. **Add Monitoring** - CloudWatch, Prometheus, Grafana
5. **Enhance AI Features** - Add agents, knowledge bases, action groups

## Documentation

- **Setup Guide:** `EC2_DEMO_SETUP.md` - Detailed EC2 setup instructions
- **API Docs:** `http://YOUR_EC2_IP:8000/api/docs` - Interactive Swagger UI
- **Code:** `api/app/routes/demo.py` - Demo endpoint implementation
- **Bedrock Adapter:** `api/app/services/bedrock_adapter.py` - Bedrock SDK wrapper

## Support

For issues or questions:

1. Check logs: `docker-compose -f docker-compose.demo.yml logs`
2. Review troubleshooting section above
3. Check AWS Bedrock service status
4. Verify IAM permissions

---

**Demo Ready!** 🚀

Simple, working, and demonstrates Amazon Bedrock integration perfectly.
