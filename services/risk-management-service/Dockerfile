# Multi-stage Rust build for Risk Management Service
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
COPY services/risk-management-service/Cargo.toml ./services/risk-management-service/

# Copy shared libraries
COPY libs/ ./libs/

# Copy service source code
COPY services/risk-management-service/src/ ./services/risk-management-service/src/

# Build the application
RUN cargo build --release --bin risk-management-service

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
COPY --from=builder /app/target/release/risk-management-service /app/risk-management-service

# Copy configuration files
COPY services/risk-management-service/config/ ./config/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Run the application
CMD ["./risk-management-service"]
