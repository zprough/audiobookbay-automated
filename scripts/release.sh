#!/bin/bash

# Release script for audiobookbay-automated
# Usage: ./scripts/release.sh [version]
# Example: ./scripts/release.sh 1.0.1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if version is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version number required${NC}"
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.1"
    exit 1
fi

VERSION=$1
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Validate version format (semantic versioning)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Version must follow semantic versioning (e.g., 1.0.1)${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Creating release $VERSION${NC}"

# Check if we're on main branch
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: You're not on the main branch (current: $CURRENT_BRANCH)${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    exit 1
fi

# Update VERSION file
echo "$VERSION" > VERSION
echo -e "${GREEN}✓ Updated VERSION file${NC}"

# Commit version update
git add VERSION
git commit -m "bump: version to $VERSION"
echo -e "${GREEN}✓ Committed version update${NC}"

# Create and push tag
git tag -a "v$VERSION" -m "Release version $VERSION"
git push origin main
git push origin "v$VERSION"
echo -e "${GREEN}✓ Created and pushed tag v$VERSION${NC}"

echo -e "${BLUE}🎉 Release $VERSION created successfully!${NC}"
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Go to https://github.com/zprough/audiobookbay-automated/releases"
echo "2. Create a new release from tag v$VERSION"
echo "3. Add release notes describing changes"
echo "4. Publish the release to trigger container build"
