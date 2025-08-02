# Multi-stage Rust build for AI Orchestration Service
FROM rust:1.75-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy workspace Cargo files
COPY Cargo.toml Cargo.lock ./
COPY services/ai-orchestration-service/Cargo.toml ./services/ai-orchestration-service/

# Copy shared libraries
COPY libs/ ./libs/

# Copy service source code
COPY services/ai-orchestration-service/src/ ./services/ai-orchestration-service/src/

# Build the application
RUN cargo build --release --bin ai-orchestration-service

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -r -s /bin/false appuser

# Create app directory
WORKDIR /app

# Copy binary from builder stage
COPY --from=builder /app/target/release/ai-orchestration-service /app/ai-orchestration-service

# Copy configuration files
COPY services/ai-orchestration-service/config/ ./config/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8085/health || exit 1

# Run the application
CMD ["./ai-orchestration-service"]
