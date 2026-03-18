FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-c", "from csvglow.mcp_server import mcp; mcp.run(transport='stdio')"]
