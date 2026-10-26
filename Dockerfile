FROM python:3.12-slim
LABEL io.modelcontextprotocol.server.name="io.github.CYAN-ECLIPSE-TECHNOLOGIES-LLC/bazaar"
WORKDIR /app
COPY server.py catalog.json bazaar-manifest.json ./
COPY src ./src
RUN useradd -r appuser
USER appuser
ENTRYPOINT ["python", "server.py"]
