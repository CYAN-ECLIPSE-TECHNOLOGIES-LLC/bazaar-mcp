FROM python:3.12-slim
WORKDIR /app
COPY server.py catalog.json bazaar-manifest.json ./
RUN useradd -r appuser
USER appuser
ENTRYPOINT ["python", "server.py"]
