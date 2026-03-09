#!/bin/bash

# Script to check available container versions
# Usage: ./scripts/check-versions.sh

set -e

REPO="zprough/audiobookbay-automated"
REGISTRY_URL="ghcr.io"

echo "🐳 Available container versions for $REGISTRY_URL/$REPO:"
echo

# Check if gh CLI is available
if command -v gh &> /dev/null; then
    echo "📦 GitHub Releases:"
    gh release list --repo $REPO | head -10
    echo
fi

# Check current local version
if [ -f VERSION ]; then
    echo "📋 Current version: $(cat VERSION)"
    echo
fi

# Show some useful commands
echo "🔧 Useful commands:"
echo "  • Pull latest:     docker pull $REGISTRY_URL/$REPO:latest"
echo "  • Pull specific:   docker pull $REGISTRY_URL/$REPO:v1.0.2"
echo "  • List local:      docker images $REGISTRY_URL/$REPO"
echo "  • Create release:  ./scripts/release.sh <version>"
