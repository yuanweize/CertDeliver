#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running local checks...${NC}"

# Run local checks first
if ./venv/bin/ruff check . && ./venv/bin/ruff format --check . && ./venv/bin/mypy src/certdeliver --ignore-missing-imports && ./venv/bin/pytest; then
    echo -e "${GREEN}Local checks passed!${NC}"
else
    echo -e "${RED}Local checks failed. Aborting push.${NC}"
    exit 1
fi

# Push changes
echo -e "${YELLOW}Pushing changes...${NC}"
git push

# Check for gh cli
if command -v gh &> /dev/null; then
    echo -e "${YELLOW}Waiting for workflow to start...${NC}"
    sleep 5
    echo -e "${YELLOW}Watching latest workflow run...${NC}"
    gh run watch $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')
    
    # Get status
    STATUS=$(gh run list --limit 1 --json conclusion --jq '.[0].conclusion')
    if [ "$STATUS" == "success" ]; then
        echo -e "${GREEN}CI Pipeline Passed!${NC}"
        exit 0
    else
        echo -e "${RED}CI Pipeline Failed!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}GitHub CLI (gh) not found.${NC}"
    echo "Please check status manually at: https://github.com/yuanweize/CertDeliver/actions"
fi
