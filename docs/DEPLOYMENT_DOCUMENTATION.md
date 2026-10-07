# Deployment & DevOps Documentation

## Current Environment Management
The system uses `.env` for local configuration (`AI_PROVIDER`, `OLLAMA_BASE_URL`, `GEMINI_API_KEY`).
The application is run manually via `npm install`, `pip install`, and `npm run dev`.

## Production Docker Architecture Recommendation

To deploy this in an enterprise environment, the architecture must be containerized.

```dockerfile
# Concept:
- Frontend Container (Nginx serving built Vite static files)
- API Backend (Node.js/Express)
- Worker Backend (FastAPI/Python for orchestrator and OpenXML engines)
- Database (PostgreSQL with pgvector for RAG)
- Cache/Queue (Redis)
```

## CI/CD Pipeline Strategy

1. **Linting & formatting**: `eslint` for TS, `flake8`/`black` for Python.
2. **Testing**: Run Python unit tests (`python -m unittest`) and frontend tests on every Pull Request.
3. **Security Scans**: Use Bandit (Python) and npm audit for dependencies.
4. **Docker Build**: Build multi-architecture images and push to ECR/ACR.
5. **Deployment**: Deploy via Helm to Kubernetes, or AWS ECS.

## Scalability
The current `child_process.spawn` in Node.js creates a massive bottleneck (spinning up Python VM for every API call). 
**Horizontal Scaling**:
- Expose the Python engine as a permanent FastAPI service.
- Use Celery workers consuming from a Redis queue for document generation, as generation can take 30+ seconds depending on the LLM.
- Place an API Gateway in front of the services.
