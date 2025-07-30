#!/bin/bash
# RegulensAI Database Backup Script
# Enterprise-grade automated backup with S3 integration and monitoring

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment variables with defaults
DATABASE_URL="${DATABASE_URL:-postgresql://regulens:password@localhost:5432/regulens_training}"
S3_BUCKET="${S3_BUCKET:-regulensai-backups}"
BACKUP_PREFIX="${BACKUP_PREFIX:-training-portal}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPRESSION_LEVEL="${COMPRESSION_LEVEL:-6}"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Derived variables
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="${BACKUP_PREFIX}_backup_${TIMESTAMP}.sql"
COMPRESSED_FILENAME="${BACKUP_FILENAME}.gz"
LOCAL_BACKUP_DIR="/backups"
LOG_FILE="${LOCAL_BACKUP_DIR}/backup.log"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# NOTIFICATION FUNCTIONS
# ============================================================================

send_notification() {
    local status="$1"
    local message="$2"
    
    if [[ -n "$NOTIFICATION_WEBHOOK" ]]; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"RegulensAI Backup $status\",
                \"attachments\": [{
                    \"color\": \"$([ "$status" = "SUCCESS" ] && echo "good" || echo "danger")\",
                    \"fields\": [{
                        \"title\": \"Environment\",
                        \"value\": \"$ENVIRONMENT\",
                        \"short\": true
                    }, {
                        \"title\": \"Timestamp\",
                        \"value\": \"$TIMESTAMP\",
                        \"short\": true
                    }, {
                        \"title\": \"Message\",
                        \"value\": \"$message\",
                        \"short\": false
                    }]
                }]
            }" \
            --silent --show-error || log_error "Failed to send notification"
    fi
}

# ============================================================================
# BACKUP FUNCTIONS
# ============================================================================

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check required tools
    for tool in pg_dump gzip aws; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' not found"
            exit 1
        fi
    done
    
    # Check database connectivity
    if ! pg_isready -d "$DATABASE_URL" -q; then
        log_error "Database is not accessible"
        exit 1
    fi
    
    # Check S3 access
    if ! aws s3 ls "s3://$S3_BUCKET" &> /dev/null; then
        log_error "S3 bucket '$S3_BUCKET' is not accessible"
        exit 1
    fi
    
    # Create backup directory
    mkdir -p "$LOCAL_BACKUP_DIR"
    
    log_success "Prerequisites check passed"
}

create_database_backup() {
    log "Creating database backup..."
    
    local backup_path="$LOCAL_BACKUP_DIR/$BACKUP_FILENAME"
    
    # Create backup with custom format for better compression and features
    pg_dump "$DATABASE_URL" \
        --format=custom \
        --compress=0 \
        --verbose \
        --file="$backup_path" \
        2>> "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Database backup created: $backup_path"
        
        # Get backup size
        local backup_size=$(du -h "$backup_path" | cut -f1)
        log "Backup size: $backup_size"
        
        return 0
    else
        log_error "Database backup failed"
        return 1
    fi
}

compress_backup() {
    log "Compressing backup..."
    
    local backup_path="$LOCAL_BACKUP_DIR/$BACKUP_FILENAME"
    local compressed_path="$LOCAL_BACKUP_DIR/$COMPRESSED_FILENAME"
    
    gzip -"$COMPRESSION_LEVEL" "$backup_path"
    
    if [[ $? -eq 0 ]]; then
        local compressed_size=$(du -h "$compressed_path" | cut -f1)
        log_success "Backup compressed: $compressed_size"
        return 0
    else
        log_error "Backup compression failed"
        return 1
    fi
}

upload_to_s3() {
    log "Uploading backup to S3..."
    
    local compressed_path="$LOCAL_BACKUP_DIR/$COMPRESSED_FILENAME"
    local s3_path="s3://$S3_BUCKET/database/$ENVIRONMENT/$COMPRESSED_FILENAME"
    
    aws s3 cp "$compressed_path" "$s3_path" \
        --storage-class STANDARD_IA \
        --metadata "environment=$ENVIRONMENT,timestamp=$TIMESTAMP,type=database" \
        2>> "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Backup uploaded to S3: $s3_path"
        return 0
    else
        log_error "S3 upload failed"
        return 1
    fi
}

cleanup_local_files() {
    log "Cleaning up local files..."
    
    # Remove compressed backup file
    rm -f "$LOCAL_BACKUP_DIR/$COMPRESSED_FILENAME"
    
    # Clean up old local backups (older than 7 days)
    find "$LOCAL_BACKUP_DIR" -name "${BACKUP_PREFIX}_backup_*.sql.gz" -mtime +7 -delete
    
    # Clean up old log files (older than 30 days)
    find "$LOCAL_BACKUP_DIR" -name "*.log" -mtime +30 -delete
    
    log_success "Local cleanup completed"
}

cleanup_old_s3_backups() {
    log "Cleaning up old S3 backups..."
    
    # List and delete backups older than retention period
    aws s3api list-objects-v2 \
        --bucket "$S3_BUCKET" \
        --prefix "database/$ENVIRONMENT/" \
        --query "Contents[?LastModified<='$(date -d "$RETENTION_DAYS days ago" --iso-8601)'].Key" \
        --output text | \
    while read -r key; do
        if [[ -n "$key" && "$key" != "None" ]]; then
            aws s3 rm "s3://$S3_BUCKET/$key"
            log "Deleted old backup: $key"
        fi
    done
    
    log_success "S3 cleanup completed"
}

# ============================================================================
# MAIN BACKUP PROCESS
# ============================================================================

main() {
    log "Starting RegulensAI database backup process"
    log "Environment: $ENVIRONMENT"
    log "S3 Bucket: $S3_BUCKET"
    log "Retention: $RETENTION_DAYS days"
    
    local start_time=$(date +%s)
    local success=true
    
    # Execute backup steps
    if check_prerequisites && \
       create_database_backup && \
       compress_backup && \
       upload_to_s3; then
        
        cleanup_local_files
        cleanup_old_s3_backups
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log_success "Backup process completed successfully in ${duration}s"
        send_notification "SUCCESS" "Database backup completed successfully in ${duration}s"
        
    else
        success=false
        log_error "Backup process failed"
        send_notification "FAILED" "Database backup process failed. Check logs for details."
    fi
    
    # Exit with appropriate code
    if [[ "$success" == true ]]; then
        exit 0
    else
        exit 1
    fi
}

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "RegulensAI Database Backup Script"
        echo "Usage: $0 [--help|--test]"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL       - PostgreSQL connection string"
        echo "  S3_BUCKET         - S3 bucket for backup storage"
        echo "  BACKUP_PREFIX     - Prefix for backup files"
        echo "  RETENTION_DAYS    - Number of days to retain backups"
        echo "  NOTIFICATION_WEBHOOK - Slack/Teams webhook for notifications"
        echo "  ENVIRONMENT       - Environment name (production, staging, etc.)"
        exit 0
        ;;
    --test)
        log "Running backup in test mode (no S3 upload)"
        S3_BUCKET=""
        ;;
esac

# Execute main function
main "$@"
