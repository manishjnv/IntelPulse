# AWS CLI Installation Instructions

## Current Status
The automated installation failed due to permission requirements. AWS CLI needs to be installed manually with administrator privileges.

## Option 1: Manual Installation (Recommended)

### Step 1: Download AWS CLI
1. Download the AWS CLI MSI installer from:
   https://awscli.amazonaws.com/AWSCLIV2.msi

2. Or the installer has already been downloaded to:
   `%TEMP%\AWSCLIV2.msi`

### Step 2: Install with Administrator Rights
1. Right-click on `AWSCLIV2.msi`
2. Select "Run as administrator"
3. Follow the installation wizard
4. Accept the default installation path: `C:\Program Files\Amazon\AWSCLIV2\`

### Step 3: Verify Installation
Open a NEW PowerShell window (to refresh PATH) and run:
```powershell
aws --version
```

Expected output:
```
aws-cli/2.x.x Python/3.x.x Windows/10 exe/AMD64
```

## Option 2: Using Chocolatey with Admin Rights

1. Open PowerShell as Administrator (Right-click → Run as Administrator)
2. Run:
```powershell
choco install awscli -y
```

3. Close and reopen PowerShell
4. Verify:
```powershell
aws --version
```

## Option 3: Using winget (Windows Package Manager)

If you have winget installed:
```powershell
winget install Amazon.AWSCLI
```

## After Installation

### Configure AWS Credentials
```bash
aws configure
```

You'll be prompted for:
- **AWS Access Key ID**: Your AWS access key
- **AWS Secret Access Key**: Your AWS secret key
- **Default region name**: `ap-south-1` (Mumbai)
- **Default output format**: `json`

### Verify AWS Access
```bash
aws sts get-caller-identity
```

This should return your AWS account ID, user ID, and ARN.

## Next Steps After AWS CLI is Installed

1. Configure AWS credentials (see above)
2. Bootstrap CDK:
   ```bash
   cd infra
   npx cdk bootstrap aws://ACCOUNT-ID/ap-south-1
   ```
3. Deploy the stack:
   ```bash
   npx cdk deploy IntelPulseStack
   ```

## Troubleshooting

### "aws: command not found" after installation
- Close and reopen your terminal/PowerShell
- The PATH environment variable needs to be refreshed

### Installation fails with permission error
- Make sure you're running the installer as Administrator
- Try Option 2 (Chocolatey with admin rights)

### Cannot find AWS credentials
- Run `aws configure` to set up credentials
- Or set environment variables:
  ```powershell
  $env:AWS_ACCESS_KEY_ID="your-key"
  $env:AWS_SECRET_ACCESS_KEY="your-secret"
  $env:AWS_DEFAULT_REGION="ap-south-1"
  ```

## Alternative: Use AWS CloudShell

If you have access to AWS Console, you can use AWS CloudShell:
1. Log in to AWS Console
2. Click the CloudShell icon (terminal icon in top navigation)
3. CloudShell comes with AWS CLI pre-installed and pre-configured
4. Clone your repository and run CDK commands there

## Security Note

Never commit AWS credentials to git. Always use:
- AWS CLI configuration (`aws configure`)
- Environment variables
- IAM roles (when running on EC2/ECS)
- AWS SSO for temporary credentials

---

**Status**: Awaiting manual installation with administrator privileges
**Next Action**: Install AWS CLI using one of the options above, then run `aws configure`
