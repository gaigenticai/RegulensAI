# Multi-stage Docker build for RegulateAI services
# Stage 1: Build environment
FROM rust:1.75-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    libpq-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1001 regulateai

# Set working directory
WORKDIR /app

# Copy dependency files
COPY Cargo.toml Cargo.lock ./
COPY shared/ ./shared/
COPY services/ ./services/

# Build dependencies (this layer will be cached if dependencies don't change)
RUN cargo build --release --workspace

# Stage 2: Runtime environment
FROM debian:bookworm-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1001 regulateai

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/models \
    && chown -R regulateai:regulateai /app

# Copy built binaries from builder stage
COPY --from=builder /app/target/release/aml-service /app/bin/aml-service
COPY --from=builder /app/target/release/compliance-service /app/bin/compliance-service
COPY --from=builder /app/target/release/risk-management-service /app/bin/risk-management-service
COPY --from=builder /app/target/release/fraud-detection-service /app/bin/fraud-detection-service
COPY --from=builder /app/target/release/cybersecurity-service /app/bin/cybersecurity-service
COPY --from=builder /app/target/release/ai-orchestration-service /app/bin/ai-orchestration-service
COPY --from=builder /app/target/release/api-gateway /app/bin/api-gateway

# Copy configuration files
COPY config/ /app/config/
COPY migrations/ /app/migrations/

# Set ownership
RUN chown -R regulateai:regulateai /app

# Switch to non-root user
USER regulateai

# Set working directory
WORKDIR /app

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command (can be overridden)
CMD ["/app/bin/api-gateway"]

# Stage 3: Development environment
FROM builder as development

# Install development tools
RUN cargo install cargo-watch sqlx-cli

# Copy source code
COPY . .

# Set working directory
WORKDIR /app

# Switch to app user
USER regulateai

# Default command for development
CMD ["cargo", "watch", "-x", "run"]
