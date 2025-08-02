# Multi-stage Rust build for Cybersecurity Service
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
COPY services/cybersecurity-service/Cargo.toml ./services/cybersecurity-service/

# Copy shared libraries
COPY libs/ ./libs/

# Copy service source code
COPY services/cybersecurity-service/src/ ./services/cybersecurity-service/src/

# Build the application
RUN cargo build --release --bin cybersecurity-service

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
COPY --from=builder /app/target/release/cybersecurity-service /app/cybersecurity-service

# Copy configuration files
COPY services/cybersecurity-service/config/ ./config/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose port
EXPOSE 8084

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8084/health || exit 1

# Run the application
CMD ["./cybersecurity-service"]
