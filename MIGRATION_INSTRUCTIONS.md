# IntelPulse → IntelPulse Migration Instructions

## Overview
This document provides step-by-step instructions to:
1. Create a new GitHub repository named "IntelPulse"
2. Rename all "IntelPulse" references to "IntelPulse"
3. Update domain references from IntelPulse.in to intelpulse.tech

---

## Step 1: Create New GitHub Repository

### Option A: Via GitHub Web Interface
1. Go to https://github.com/manishjnv
2. Click "New repository"
3. Repository name: `IntelPulse`
4. Description: "Production-grade threat intelligence platform powered by AWS Bedrock Agent Core"
5. Public repository
6. Do NOT initialize with README (we'll push existing code)
7. Click "Create repository"

### Option B: Via GitHub CLI
```bash
gh repo create manishjnv/IntelPulse --public --description "Production-grade threat intelligence platform powered by AWS Bedrock Agent Core"
```

---

## Step 2: Clone Current Repository and Rename

```bash
# Navigate to your projects directory
cd E:/code

# Clone the current repository with a new name
git clone https://github.com/manishjnv/IntelPulse.git IntelPulse

# Navigate into the new directory
cd IntelPulse

# Remove old remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/manishjnv/IntelPulse.git
```

---

## Step 3: Global Find and Replace

### 3.1 Replace "IntelPulse" with "IntelPulse"

**PowerShell Script** (run from repository root):

```powershell
# Find and replace in all files
$files = Get-ChildItem -Recurse -File -Exclude @('*.git*', 'node_modules', '*.pyc', '__pycache__', 'dist', 'build')

foreach ($file in $files) {
    try {
        $content = Get-Content $file.FullName -Raw -ErrorAction Stop
        if ($content -match 'IntelPulse') {
            $newContent = $content -replace 'IntelPulse', 'IntelPulse'
            Set-Content -Path $file.FullName -Value $newContent -NoNewline
            Write-Host "Updated: $($file.FullName)"
        }
    }
    catch {
        # Skip binary files or files that can't be read as text
    }
}

Write-Host "IntelPulse → IntelPulse replacement complete!"
```

### 3.2 Replace "IntelPulse" (lowercase) with "intelpulse"

```powershell
foreach ($file in $files) {
    try {
        $content = Get-Content $file.FullName -Raw -ErrorAction Stop
        if ($content -match 'IntelPulse') {
            $newContent = $content -replace 'IntelPulse', 'intelpulse'
            Set-Content -Path $file.FullName -Value $newContent -NoNewline
            Write-Host "Updated: $($file.FullName)"
        }
    }
    catch {
        # Skip binary files
    }
}

Write-Host "IntelPulse → intelpulse replacement complete!"
```

### 3.3 Replace Domain References

```powershell
# Replace IntelPulse.in with intelpulse.tech
foreach ($file in $files) {
    try {
        $content = Get-Content $file.FullName -Raw -ErrorAction Stop
        if ($content -match 'IntelPulse\.in') {
            $newContent = $content -replace 'IntelPulse\.in', 'intelpulse.tech'
            Set-Content -Path $file.FullName -Value $newContent -NoNewline
            Write-Host "Updated: $($file.FullName)"
        }
    }
    catch {
        # Skip binary files
    }
}

Write-Host "Domain replacement complete!"
```

---

## Step 4: Manual Updates Required

Some files may need manual review and updates:

### 4.1 Update README.md
- Change title to "IntelPulse"
- Update domain references
- Update repository URL

### 4.2 Update package.json (ui/)
```json
{
  "name": "intelpulse-ui",
  "description": "IntelPulse Threat Intelligence Platform - Frontend"
}
```

### 4.3 Update pyproject.toml (api/)
```toml
[project]
name = "intelpulse-api"
description = "IntelPulse Threat Intelligence Platform - Backend API"
```

### 4.4 Update Docker Compose
```yaml
services:
  api:
    container_name: intelpulse-api
    image: intelpulse/api:latest
  
  ui:
    container_name: intelpulse-ui
    image: intelpulse/ui:latest
  
  worker:
    container_name: intelpulse-worker
    image: intelpulse/worker:latest
```

### 4.5 Update Environment Variables
```bash
# .env.example
DOMAIN=intelpulse.tech
DOMAIN_UI=https://intelpulse.tech
DOMAIN_API=https://intelpulse.tech
```

### 4.6 Update Favicon and Logo
- Replace `ui/public/favicon.svg` with IntelPulse branding
- Update any logo images in the UI

### 4.7 Update Page Titles
```typescript
// ui/src/app/layout.tsx
export const metadata = {
  title: 'IntelPulse - Threat Intelligence Platform',
  description: 'Production-grade threat intelligence aggregation and analysis'
}
```

---

## Step 5: Verify Changes

```bash
# Search for any remaining "IntelPulse" references
grep -r "IntelPulse" . --exclude-dir={node_modules,.git,dist,build}

# Search for any remaining "IntelPulse.in" references
grep -r "IntelPulse\.in" . --exclude-dir={node_modules,.git,dist,build}

# If any found, manually update them
```

---

## Step 6: Update Git History (Optional)

If you want to clean up commit messages:

```bash
# Create a new branch for AWS migration
git checkout -b aws-migration

# Commit all changes
git add .
git commit -m "feat: rebrand IntelPulse to IntelPulse for AWS migration

- Rename all IntelPulse references to IntelPulse
- Update domain from IntelPulse.in to intelpulse.tech
- Update branding, logos, and metadata
- Prepare for AWS Bedrock Agent Core integration"
```

---

## Step 7: Push to New Repository

```bash
# Push to new repository
git push -u origin main

# Push aws-migration branch
git push -u origin aws-migration

# Verify on GitHub
# Visit: https://github.com/manishjnv/IntelPulse
```

---

## Step 8: Update GitHub Repository Settings

1. **About Section**:
   - Description: "Production-grade threat intelligence platform powered by AWS Bedrock Agent Core"
   - Website: https://intelpulse.tech
   - Topics: `threat-intelligence`, `aws`, `bedrock`, `fastapi`, `nextjs`, `cybersecurity`, `soc`, `ioc-analysis`

2. **README Badges** (add to top of README.md):
```markdown
![AWS](https://img.shields.io/badge/AWS-Bedrock-FF9900?logo=amazon-aws)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js_14-000000?logo=next.js&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-FDB515?logo=timescale&logoColor=black)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?logo=opensearch&logoColor=white)
```

3. **Branch Protection**:
   - Protect `main` branch
   - Require pull request reviews
   - Require status checks to pass

---

## Step 9: Update External Services

### 9.1 Google OAuth
1. Go to Google Cloud Console
2. Create new OAuth 2.0 Client ID for IntelPulse
3. Authorized redirect URIs:
   - https://intelpulse.tech/api/v1/auth/google/callback
   - http://localhost:3000/api/v1/auth/google/callback (for local dev)

### 9.2 Domain Registration
1. Register intelpulse.tech (if not already done)
2. Point nameservers to Route 53 (after AWS deployment)

### 9.3 External API Keys
- Keep existing API keys (VT, AbuseIPDB, OTX, Shodan, NVD)
- Update any service names in API provider dashboards

---

## Step 10: Verification Checklist

- [ ] New repository created at github.com/manishjnv/IntelPulse
- [ ] All "IntelPulse" references replaced with "IntelPulse"
- [ ] All "IntelPulse.in" references replaced with "intelpulse.tech"
- [ ] README.md updated with new branding
- [ ] package.json and pyproject.toml updated
- [ ] Docker Compose updated
- [ ] Environment variables updated
- [ ] Favicon and logos updated
- [ ] Page titles and metadata updated
- [ ] No remaining old references (verified with grep)
- [ ] Changes committed to git
- [ ] Code pushed to new repository
- [ ] GitHub repository settings configured
- [ ] Google OAuth client created
- [ ] Domain registered (or planned)

---

## Quick Command Summary

```bash
# 1. Clone and setup
cd E:/code
git clone https://github.com/manishjnv/IntelPulse.git IntelPulse
cd IntelPulse
git remote remove origin
git remote add origin https://github.com/manishjnv/IntelPulse.git

# 2. Run PowerShell replacement scripts (see Step 3)

# 3. Create migration branch
git checkout -b aws-migration

# 4. Commit changes
git add .
git commit -m "feat: rebrand IntelPulse to IntelPulse for AWS migration"

# 5. Push to new repository
git push -u origin main
git push -u origin aws-migration
```

---

## Troubleshooting

### Issue: Binary files corrupted after replacement
**Solution**: Exclude binary files from replacement:
```powershell
$files = Get-ChildItem -Recurse -File -Exclude @('*.git*', 'node_modules', '*.pyc', '__pycache__', 'dist', 'build', '*.png', '*.jpg', '*.svg', '*.ico', '*.woff', '*.woff2', '*.ttf')
```

### Issue: Git push rejected
**Solution**: Force push (only if new repository):
```bash
git push -u origin main --force
```

### Issue: Some files still have old references
**Solution**: Use VS Code global search and replace:
1. Open IntelPulse folder in VS Code
2. Ctrl+Shift+H (Find and Replace in Files)
3. Find: `IntelPulse`
4. Replace: `IntelPulse`
5. Replace All

---

## Next Steps After Migration

1. Update AWS CDK stack with new names
2. Update ECS service names
3. Update ECR repository names
4. Update Secrets Manager secret name
5. Deploy to AWS with new branding
6. Update documentation with new URLs
7. Record demo video with IntelPulse branding

---

## Support

If you encounter issues during migration:
1. Check git status: `git status`
2. Review changes: `git diff`
3. Verify no broken imports: Run tests locally
4. Check Docker builds: `docker-compose build`

---

**Estimated Time**: 1-2 hours
**Difficulty**: Medium
**Risk**: Low (new repository, no production impact)
