FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .
COPY opa/ /app/opa/
COPY openfga/ /app/openfga/
EXPOSE 8500
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r=httpx.get('http://localhost:8500/health'); exit(0 if r.status_code==200 else 1)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8500"]

FROM base AS test
COPY pytest.ini .
COPY tests/ /app/tests/
RUN pip install --no-cache-dir pytest pytest-asyncio respx
CMD ["python", "-m", "pytest", "tests/", "-v", "--ignore=tests/test_kc_lago_sync.py", "--ignore=tests/test_integration.py"]
