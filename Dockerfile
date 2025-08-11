# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install OS packages required for uv and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (https://github.com/astral-sh/uv)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy dependency metadata first (leverages Docker layer caching)
COPY pyproject.toml /app/pyproject.toml

# Create virtualenv and install dependencies (including dev extras for test profile)
RUN uv venv && uv sync --extra dev

# Copy source code. A bind mount will override this in development
COPY src /app/src
COPY hello_llm.py /app/hello_llm.py

# Ensure data directory exists for persisted sessions
RUN mkdir -p /app/data

EXPOSE 8501

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Run Streamlit via uv
CMD ["uv", "run", "streamlit", "run", "src/ai_tutor/app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]


