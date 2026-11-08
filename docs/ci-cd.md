
# CI/CD Pipeline

## Overview

This project uses GitHub Actions to automate code quality checks, dependency vulnerability scanning, automated testing, Docker image building, and container image security scanning.

The workflow runs on:
- Pull requests targeting `master`.
- Pushes to `master`.

Docker images are published to GitHub Container Registry (GHCR) only when changes are pushed to `master`.

## Pipeline Execution

The table below shows which steps run for each workflow trigger.

| Workflow Step | Pull Request to master | Push to master |
|---|---|---|
| Checkout source code | ✓ | ✓ |
| Set up Python | ✓ | ✓ |
| Ruff linting | ✓ | ✓ |
| Dependency vulnerability audit | ✓ | ✓ |
| Run tests | ✓ | ✓ |
| Build Docker image | ✓ | ✓ |
| Scan Docker image with Trivy | ✓ | ✓ |
| Authenticate with GHCR | - | ✓ |
| Push Docker image to GHCR | - | ✓ |

Pull requests validate changes without publishing Docker images. Images are published only after changes reach `master`.

## Code Quality and Dependency Auditing

### Ruff

[Ruff](https://docs.astral.sh/ruff/) is used to lint the Python codebase.

It identifies common programming errors, style violations, and other code quality issues. Ruff runs inside the Docker test stage before pytest.

### pip-audit

[pip-audit](https://github.com/pypa/pip-audit) checks the project's Python dependencies against known vulnerability advisories.

It scans the dependencies listed in `requirements.txt`.

The workflow fails if vulnerabilities are detected.

These tools serve different purposes: Ruff checks code quality, while pip-audit checks third-party Python dependencies for known security vulnerabilities.

## Automated Testing

The workflow runs the project's test suite using pytest.

Tests execute inside a dedicated Docker test stage, which installs the application dependencies and development dependencies required for testing.

The test environment uses a separate `.env.test` configuration and SQLite rather than the development PostgreSQL database.

This keeps automated tests isolated from the development database and avoids requiring a running PostgreSQL service in the CI environment.

## Docker Build and Image Scanning

### Multi-stage Docker Build

The Dockerfile uses separate stages for the application and testing environments.

| Stage | Purpose |
|---|---|
| `app` | Builds the application image |
| `test` | Installs testing dependencies and runs Ruff and pytest |

### Trivy

[Trivy](https://trivy.dev/) is used to scan the built Docker image for known vulnerabilities including operating system packages and application dependencies.

The configuration:

- Scans for HIGH and CRITICAL vulnerabilities.
- Ignores vulnerabilities without an available fix.
- Fails the workflow when qualifying vulnerabilities are found.

## Docker Image Publishing

Docker images are published to GitHub Container Registry (GHCR).

Publishing occurs only on pushes to `master`.

The workflow authenticates using GitHub's automatically provided `GITHUB_TOKEN`, with the required `packages: write` permission.

Two tags are published:

| Tag | Purpose |
|---|---|
| `latest` | Identifies the most recently published image |
| Commit SHA | Identifies the source commit associated with the image |

## Local Workflow Testing with act

[act](https://github.com/nektos/act) is used to execute GitHub Actions workflows locally using Docker.

This allows the workflow to be tested before relying on GitHub-hosted runners.

The pull request workflow can be triggered locally with:

```bash
act pull_request -s GITHUB_TOKEN="$(gh auth token)"
```

The GitHub CLI is used to retrieve an authentication token for local workflow execution.

## Security Considerations

Several security practices are incorporated into the pipeline:

- Dependency vulnerability scanning with pip-audit.
- Container image vulnerability scanning with Trivy.
- Docker image publishing restricted to pushes to master.
- GHCR authentication using `GITHUB_TOKEN` instead of a manually managed personal access token.
- GitHub Actions workflow permissions.
- Docker image tagging with commit SHAs for traceability.

These checks help identify common code and dependency security issues before images are published.

They do not replace a comprehensive security review or runtime security controls.

## Limitations and Future Improvements

The current pipeline focuses on code quality, automated testing, dependency auditing, Docker image security, and image publishing.

Potential improvements include:

- **Secret scanning:** Detect accidentally committed credentials and secrets.
- **Static Application Security Testing (SAST):** Identify potential security weaknesses in application code.
- **Integration testing:** Test interactions with services such as PostgreSQL and S3-compatible storage.
- **Image signing:** Verify the authenticity and integrity of published container images.
- **Deployment automation:** Automatically deploy validated images to a Kubernetes environment.
- **Improved image versioning:** Introduce a more structured release and tagging strategy.
- **Permission scoping:** Separate validation and publishing jobs and grant each job only the permissions it requires.
- **Action pinning:** Pin third-party GitHub Actions to full commit SHAs for stronger supply-chain security.

These improvements can be introduced as the project evolves.
