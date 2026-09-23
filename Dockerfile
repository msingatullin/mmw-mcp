FROM python:3.12-slim

WORKDIR /app

# Install standard dependencies
RUN pip install --no-cache-dir "mcp[cli]>=1.0.0" pydantic httpx

# Create a lightweight client runner / introspector for Glama CI
COPY introspect.py /app/introspect.py

ENV PORT=8000
EXPOSE 8000

CMD ["python", "/app/introspect.py"]
