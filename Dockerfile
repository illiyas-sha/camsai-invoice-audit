FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Chroma's ~80MB embedding model now, using chromadb's own API
# directly - deliberately *before* COPY . . so this expensive step's cache
# only invalidates when requirements.txt changes, never when application
# source code changes. Getting this ordering wrong (source copied first)
# means every source edit forces an ~8 minute re-download on next build.
RUN python -c "import chromadb.utils.embedding_functions as ef; ef.DefaultEmbeddingFunction()(['warmup'])"

COPY . .

# Seed the vendor-contract collection into the image. Fast - the embedding
# model is already cached from the step above, this just computes a
# handful of short embeddings, so routine source edits stay cheap to rebuild.
RUN python -c "from mcp_server.vectorstore.chroma_store import get_collection; get_collection()"

CMD ["python", "-m", "app.run", "--scenario", "a"]
