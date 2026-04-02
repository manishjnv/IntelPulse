# IntelWatch to IntelPulse Rebranding Script
# This script performs global find and replace across the entire codebase

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IntelWatch → IntelPulse Rebranding Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Confirm before proceeding
$confirmation = Read-Host "This will modify files in the current directory. Continue? (yes/no)"
if ($confirmation -ne 'yes') {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit
}

Write-Host ""
Write-Host "Starting rebranding process..." -ForegroundColor Green
Write-Host ""

# Define exclusions
$excludeDirs = @(
    '.git',
    'node_modules',
    '__pycache__',
    'dist',
    'build',
    '.next',
    'venv',
    'env',
    '.venv'
)

$excludeExtensions = @(
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.so',
    '*.dll',
    '*.exe',
    '*.bin',
    '*.png',
    '*.jpg',
    '*.jpeg',
    '*.gif',
    '*.ico',
    '*.svg',
    '*.woff',
    '*.woff2',
    '*.ttf',
    '*.eot',
    '*.mp4',
    '*.mp3',
    '*.zip',
    '*.tar',
    '*.gz'
)

# Get all text files
Write-Host "Scanning files..." -ForegroundColor Yellow
$files = Get-ChildItem -Recurse -File | Where-Object {
    $file = $_
    $excluded = $false
    
    # Check if in excluded directory
    foreach ($dir in $excludeDirs) {
        if ($file.FullName -like "*\$dir\*") {
            $excluded = $true
            break
        }
    }
    
    # Check if excluded extension
    if (-not $excluded) {
        foreach ($ext in $excludeExtensions) {
            if ($file.Name -like $ext) {
                $excluded = $true
                break
            }
        }
    }
    
    -not $excluded
}

Write-Host "Found $($files.Count) files to process" -ForegroundColor Green
Write-Host ""

# Counters
$totalUpdated = 0
$errors = 0

# Replacement patterns
$replacements = @(
    @{
        Pattern = 'IntelWatch'
        Replacement = 'IntelPulse'
        Description = 'IntelWatch → IntelPulse'
    },
    @{
        Pattern = 'intelwatch'
        Replacement = 'intelpulse'
        Description = 'intelwatch → intelpulse'
    },
    @{
        Pattern = 'INTELWATCH'
        Replacement = 'INTELPULSE'
        Description = 'INTELWATCH → INTELPULSE'
    },
    @{
        Pattern = 'intelwatch\.in'
        Replacement = 'intelpulse.tech'
        Description = 'intelwatch.in → intelpulse.tech'
    },
    @{
        Pattern = 'ti-platform'
        Replacement = 'IntelPulse'
        Description = 'ti-platform → IntelPulse'
    }
)

# Process each replacement
foreach ($replacement in $replacements) {
    Write-Host "Processing: $($replacement.Description)" -ForegroundColor Cyan
    $count = 0
    
    foreach ($file in $files) {
        try {
            $content = Get-Content $file.FullName -Raw -ErrorAction Stop
            
            if ($content -match $replacement.Pattern) {
                $newContent = $content -replace $replacement.Pattern, $replacement.Replacement
                Set-Content -Path $file.FullName -Value $newContent -NoNewline
                $count++
                Write-Host "  ✓ $($file.FullName)" -ForegroundColor Gray
            }
        }
        catch {
            # Skip binary files or files that can't be read as text
            $errors++
        }
    }
    
    Write-Host "  Updated $count files" -ForegroundColor Green
    $totalUpdated += $count
    Write-Host ""
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Rebranding Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total files updated: $totalUpdated" -ForegroundColor Green
Write-Host "Errors (skipped): $errors" -ForegroundColor Yellow
Write-Host ""

# Verification
Write-Host "Running verification..." -ForegroundColor Yellow
Write-Host ""

$remainingIntelWatch = Select-String -Path $files.FullName -Pattern "IntelWatch" -SimpleMatch -ErrorAction SilentlyContinue
$remainingDomain = Select-String -Path $files.FullName -Pattern "intelwatch\.in" -ErrorAction SilentlyContinue

if ($remainingIntelWatch) {
    Write-Host "⚠ Warning: Found remaining 'IntelWatch' references:" -ForegroundColor Yellow
    $remainingIntelWatch | ForEach-Object {
        Write-Host "  $($_.Path):$($_.LineNumber)" -ForegroundColor Gray
    }
    Write-Host ""
}

if ($remainingDomain) {
    Write-Host "⚠ Warning: Found remaining 'intelwatch.in' references:" -ForegroundColor Yellow
    $remainingDomain | ForEach-Object {
        Write-Host "  $($_.Path):$($_.LineNumber)" -ForegroundColor Gray
    }
    Write-Host ""
}

if (-not $remainingIntelWatch -and -not $remainingDomain) {
    Write-Host "✓ Verification passed! No remaining old references found." -ForegroundColor Green
    Write-Host ""
}

# Next steps
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Review changes: git diff" -ForegroundColor White
Write-Host "2. Test locally: docker-compose build" -ForegroundColor White
Write-Host "3. Commit changes: git add . && git commit -m 'feat: rebrand to IntelPulse'" -ForegroundColor White
Write-Host "4. Push to new repo: git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "For detailed instructions, see MIGRATION_INSTRUCTIONS.md" -ForegroundColor Yellow
Write-Host ""

# Offer to create git commit
$gitCommit = Read-Host "Create git commit now? (yes/no)"
if ($gitCommit -eq 'yes') {
    Write-Host ""
    Write-Host "Creating git commit..." -ForegroundColor Green
    
    git add .
    git commit -m "feat: rebrand IntelWatch to IntelPulse for AWS migration

- Rename all IntelWatch references to IntelPulse
- Update domain from intelwatch.in to intelpulse.tech
- Update repository name from ti-platform to IntelPulse
- Update branding, logos, and metadata
- Prepare for AWS Bedrock Agent Core integration

This rebranding is part of the AWS Codethon submission for Theme 3:
Intelligent Multi-Agent Domain Solutions"
    
    Write-Host ""
    Write-Host "✓ Commit created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To push to new repository:" -ForegroundColor Yellow
    Write-Host "  git remote add origin https://github.com/manishjnv/IntelPulse.git" -ForegroundColor White
    Write-Host "  git push -u origin main" -ForegroundColor White
    Write-Host ""
}

Write-Host "Done! 🚀" -ForegroundColor Green
