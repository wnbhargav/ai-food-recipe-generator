# Verification

Local verification on 2026-09-29, Windows, Python 3.12:

- Editable package installation completed successfully.
- 22 pytest tests passed.
- Ruff lint and formatting checks passed.
- Browser JavaScript passed `node --check`.
- The browser form returned a chickpea curry with quantities, steps, additional ingredients, and retrieved context after keyboard submission.

The test client emits an upstream Starlette deprecation warning about its HTTPX integration; the tests pass.

Live inference was not run against downloaded Ollama models. The provider workflow is covered with mocked HTTP requests, including embedding retrieval, cache reuse, structured generation, and invalid-output handling. Docker engine was unavailable locally, so the Docker build and Kubernetes manifests were not executed. GitHub Actions has not run until the repository is pushed.

No recipe-quality benchmark, nutrition verification, or allergen verification has been performed.
