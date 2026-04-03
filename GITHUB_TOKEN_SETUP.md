# GitHub Access Token Configuration Guide

## Current Git Configuration
- **Username**: Manish Kumar
- **Email**: manishjnvk@live.com
- **Remote**: https://github.com/manishjnv/IntelPulse.git
- **Branch**: aws-migration

## Option 1: Git Credential Manager (Recommended for Windows)

Git Credential Manager (GCM) is the easiest way to manage GitHub tokens on Windows.

### Check if GCM is installed:
```powershell
git credential-manager --version
```

### Configure GCM to use your token:
```powershell
# Set credential helper
git config --global credential.helper manager-core

# Next time you push, you'll be prompted for credentials
# Username: your-github-username
# Password: paste-your-github-token (not your password!)
```

### Test it:
```bash
git push origin aws-migration
```

When prompted:
- **Username**: `manishjnv` (or your GitHub username)
- **Password**: Paste your GitHub Personal Access Token

GCM will store the token securely in Windows Credential Manager.

## Option 2: Store Token in Git Config (Simple but less secure)

### Configure git to use the token in the remote URL:
```bash
git remote set-url origin https://YOUR_TOKEN@github.com/manishjnv/IntelPulse.git
```

Replace `YOUR_TOKEN` with your actual GitHub token.

### Verify:
```bash
git remote -v
```

### Test:
```bash
git push origin aws-migration
```

**Warning**: This stores the token in plain text in `.git/config`. Don't share this file.

## Option 3: Use Environment Variable

### Set the token as an environment variable:
```powershell
# For current session only
$env:GITHUB_TOKEN = "your_token_here"

# For permanent (add to PowerShell profile)
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'your_token_here', 'User')
```

### Configure git to use it:
```bash
git config --global credential.helper store
```

### When pushing, use:
```bash
git push https://$env:GITHUB_TOKEN@github.com/manishjnv/IntelPulse.git aws-migration
```

## Option 4: GitHub CLI (gh)

### Install GitHub CLI:
```powershell
choco install gh -y
# Or download from: https://cli.github.com/
```

### Authenticate:
```bash
gh auth login
```

Select:
- GitHub.com
- HTTPS
- Paste an authentication token
- Paste your token

### Test:
```bash
gh auth status
git push origin aws-migration
```

## Quick Setup (Recommended)

I'll help you set up Option 1 (GCM). Run these commands:

```powershell
# 1. Configure credential helper
git config --global credential.helper manager-core

# 2. Try to push (you'll be prompted for token)
git push origin aws-migration
```

When the credential prompt appears:
1. **Username**: Enter your GitHub username
2. **Password**: Paste your GitHub Personal Access Token (starts with `ghp_` or `github_pat_`)

The token will be stored securely and you won't need to enter it again.

## Verify Your Token Has Correct Permissions

Your GitHub token needs these scopes:
- ✅ `repo` (full control of private repositories)
- ✅ `workflow` (if using GitHub Actions)
- ✅ `write:packages` (if using GitHub Packages/Container Registry)

To check/create a token:
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`, `write:packages`
4. Generate and copy the token

## Current Status

You have commits ready to push:
```bash
git log origin/aws-migration..HEAD --oneline
```

After configuring the token, push with:
```bash
git push origin aws-migration
```

## Troubleshooting

### "Authentication failed"
- Make sure you're using the token, not your password
- Verify token has `repo` scope
- Check token hasn't expired

### "remote: Support for password authentication was removed"
- GitHub no longer accepts passwords
- You must use a Personal Access Token

### Token not being saved
- Make sure credential helper is configured:
  ```bash
  git config --global credential.helper manager-core
  ```

### Want to update stored token
```powershell
# Remove old credentials
git credential-manager delete https://github.com

# Next push will prompt for new token
git push origin aws-migration
```

## Security Best Practices

1. ✅ Never commit tokens to git
2. ✅ Use tokens with minimal required scopes
3. ✅ Set token expiration dates
4. ✅ Rotate tokens regularly
5. ✅ Use different tokens for different machines/purposes
6. ❌ Don't share tokens
7. ❌ Don't store tokens in plain text files

## Next Steps After Token Setup

1. Push current commits:
   ```bash
   git push origin aws-migration
   ```

2. Verify on GitHub:
   ```
   https://github.com/manishjnv/IntelPulse/tree/aws-migration
   ```

3. Continue with AWS infrastructure tasks

---

**Ready to configure?** Let me know if you want me to help you set up any of these options!
