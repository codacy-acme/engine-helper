#!/bin/bash

# Local Codacy Container Scanning Test Script
# Uses Codacy CLI v2: https://github.com/codacy/codacy-cli-v2

set -e

echo "=========================================="
echo "Codacy Container Scanning - Local Test"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODACY_CLI_SCRIPT="${SCRIPT_DIR}/.codacy-cli.sh"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Download Codacy CLI v2 wrapper script if not already present
if [ ! -f "${CODACY_CLI_SCRIPT}" ]; then
    echo "Downloading Codacy CLI v2..."
    curl -Ls https://raw.githubusercontent.com/codacy/codacy-cli-v2/main/codacy-cli.sh -o "${CODACY_CLI_SCRIPT}"
    bash "${CODACY_CLI_SCRIPT}" download
    echo "✓ Codacy CLI v2 ready"
    echo ""
fi

# Build the Docker image
echo "Step 1: Building Docker image..."
IMAGE_TAG="engine-helper:local-test"
docker build -t "${IMAGE_TAG}" .
echo "✓ Docker image built: ${IMAGE_TAG}"
echo ""

if [ -z "$CODACY_API_TOKEN" ]; then
    echo "Step 2: Running local container scan (no upload)..."
    echo "To also upload results to Codacy, set CODACY_API_TOKEN and re-run."
    echo ""
    bash "${CODACY_CLI_SCRIPT}" container-scan "${IMAGE_TAG}"
else
    echo "Step 2: Generating SBOM and uploading to Codacy..."
    echo ""
    bash "${CODACY_CLI_SCRIPT}" upload-sbom \
        -a "${CODACY_API_TOKEN}" \
        -p gh \
        -o codacy-acme \
        -r engine-helper \
        "${IMAGE_TAG}"
fi

echo ""
echo "=========================================="
echo "Local test completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review any vulnerabilities reported above"
echo "2. Check Codacy dashboard at: https://app.codacy.com"
echo "3. Once verified, commit and push to GitHub:"
echo "   - git add Dockerfile .github/workflows/codacy-container-scan.yml"
echo "   - git commit -m 'Add Codacy container scanning workflow'"
echo "   - git push origin container-scan"
echo ""
