# Codacy Container Scanning Setup

This repository now includes Codacy container scanning capabilities for security analysis of Docker images.

## Files Added

1. **Dockerfile** - Multi-stage Python build configuration for the engine-helper application
2. **.github/workflows/codacy-container-scan.yml** - GitHub Actions workflow for automated container scanning
3. **test-container-scan-local.sh** - Local testing script to verify container scanning before pushing

## Prerequisites

- Docker installed locally
- Codacy CLI token (from https://app.codacy.com/account/settings/tokens)
- The engine-helper repository must be set up in Codacy

## Local Testing

### Step 1: Set Your Codacy Token

```bash
export CODACY_CLI_TOKEN=your_token_here
```

### Step 2: Run the Local Test Script

```bash
./test-container-scan-local.sh
```

This script will:
1. Verify Docker is installed
2. Build the Docker image
3. Run Codacy container scanning (if token is set)
4. Display next steps

### Example Output

```
==========================================
Codacy Container Scanning - Local Test
==========================================

Step 1: Building Docker image...
✓ Docker image built: engine-helper:local-test

Step 2: Running Codacy container scan...
...
```

## GitHub Actions Workflow

The workflow (`codacy-container-scan.yml`) is configured to:

- **Triggers**: 
  - Push to `main` and `develop` branches
  - Pull requests to `main` and `develop` branches
  - Daily scheduled run at 2 AM UTC

- **Actions**:
  1. Checkout code
  2. Build Docker image
  3. Run Codacy container security scan via SBOM
  4. Upload scan artifacts (if available)

## GitHub Secret Configuration

Before the workflow runs on GitHub, you need to add your Codacy CLI token as a secret:

1. Go to your repository settings
2. Navigate to **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `CODACY_CLI_TOKEN`
5. Value: Your Codacy API token from https://app.codacy.com/account/settings/tokens
6. Click **Add secret**

## Monitoring Results

After deployment:

1. GitHub: Check workflow runs in **Actions** tab
2. Codacy Dashboard: https://app.codacy.com
3. Security Issues: Check the **Security** tab for container scan results

## Troubleshooting

### Local Test Issues

**Docker not found:**
```bash
# Install Docker from https://www.docker.com/products/docker-desktop
```

**Token not set:**
```bash
# Verify your token is exported
echo $CODACY_CLI_TOKEN

# If empty, export it again
export CODACY_CLI_TOKEN=your_token_here
```

### GitHub Actions Issues

**Secret not found:**
- Verify the secret is added to the repository (check **Settings** → **Secrets**)
- Secrets are not inherited from organization settings

**Scan fails with authentication error:**
- Verify the token is correct and not expired
- Check token permissions in Codacy

**Image build fails:**
- Check Docker build output
- Verify all dependencies in `requirements.txt` are installable

## Next Steps

1. ✅ Local testing: Run `./test-container-scan-local.sh`
2. Verify Docker image builds successfully
3. Commit changes to git:
   ```bash
   git add Dockerfile .github/workflows/codacy-container-scan.yml test-container-scan-local.sh
   git commit -m "Add Codacy container scanning"
   git push origin main
   ```
4. Add the `CODACY_CLI_TOKEN` secret to GitHub repository settings
5. Push a change to trigger the workflow or check **Actions** tab for scheduled runs

## Additional Resources

- [Codacy CLI Documentation](https://docs.codacy.com/codacy-cli/overview/)
- [Container Scanning Guide](https://docs.codacy.com/codacy-cli/container-scanning/)
- [SBOM Uploads](https://docs.codacy.com/codacy-cli/sbom-uploads/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
