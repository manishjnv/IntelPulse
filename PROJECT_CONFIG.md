# Project Configuration

## Workspace Directory

**Primary Location**: `E:\code\IntelPulse\ti-platform`

This is the root directory for the IntelPulse AWS migration project.

## Directory Structure

```
E:\code\IntelPulse\ti-platform\
├── .git/                   # Git repository
├── .kiro/                  # Kiro IDE configuration
│   ├── specs/             # Spec files
│   ├── steering/          # Steering rules
│   └── hooks/             # Agent hooks
├── .vscode/               # VS Code settings
├── api/                   # FastAPI backend
├── ui/                    # Next.js frontend
├── worker/                # Python RQ workers
├── infra/                 # AWS CDK infrastructure (NEW)
├── docker/                # Dockerfiles
├── db/                    # Database schemas
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Git Configuration

- **Repository**: <https://github.com/manishjnv/IntelPulse.git>
- **Current Branch**: aws-migration
- **Remote**: origin

## Terminal Configuration

All terminal commands should execute from the workspace root:

```
E:\code\IntelPulse\ti-platform
```

VS Code settings have been configured to ensure:

- Integrated terminal opens in workspace folder
- Python interpreter uses project virtual environment
- TypeScript uses project node_modules

## Verification Commands

### Check current directory

```powershell
pwd
```

Expected: `E:\code\IntelPulse\ti-platform`

### Check git root

```bash
git rev-parse --show-toplevel
```

Expected: `E:/code/IntelPulse/ti-platform`

### Check git branch

```bash
git branch --show-current
```

Expected: `aws-migration`

## Important Notes

1. **Always work from workspace root** unless specifically working in a subdirectory
2. **CDK commands** should be run from `infra/` subdirectory
3. **Python commands** should be run from `api/` subdirectory
4. **Node.js commands** for UI should be run from `ui/` subdirectory

## Quick Navigation

```powershell
# Go to workspace root
cd E:\code\IntelPulse\ti-platform

# Go to infrastructure
cd E:\code\IntelPulse\ti-platform\infra

# Go to API
cd E:\code\IntelPulse\ti-platform\api

# Go to UI
cd E:\code\IntelPulse\ti-platform\ui
```

---

**Status**: Workspace configured at `E:\code\IntelPulse\ti-platform`
**Last Updated**: 2026-04-03
