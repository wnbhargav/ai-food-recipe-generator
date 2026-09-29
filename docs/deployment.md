# Deployment notes

The app is stateless apart from its in-memory embedding cache. Each worker or replica builds its own cache on the first live request. For this ten-note corpus, a vector database would add more operational complexity than value. A larger corpus would need persistent indexing, corpus versioning, and retrieval evaluation.

## Local Kubernetes example

With a working kind cluster:

```bash
docker build -t ai-food-recipe-generator:0.1.0 .
kind load docker-image ai-food-recipe-generator:0.1.0
kubectl apply -f deploy/kubernetes.yaml
kubectl rollout status deployment/recipe-generator
kubectl port-forward service/recipe-generator 8000:80
```

The manifest runs one demo replica as a non-root user, with resource limits, a read-only filesystem, and HTTP probes. It exposes a ClusterIP service, not a public endpoint. The model runtime is not included. For live mode, supply `RECIPE_MODE=ollama` and an `OLLAMA_URL` reachable from the cluster, plus your model names. Provision model storage and compute separately.

`/health` checks the API process only. Use model-aware readiness checks before routing public live-mode traffic. The provider has a 5-second connection timeout and a 120-second request timeout. There is no automatic retry, which avoids duplicate inference work during overload.

## Before public hosting

Add authentication and rate limiting at the gateway, restrict ingress to the model service, configure HTTPS, and set an inference concurrency limit appropriate for the available hardware. Avoid logging raw pantry requests if storing them is unnecessary. This repository is a local development example, not a production service configuration.
