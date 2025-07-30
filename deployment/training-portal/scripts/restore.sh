#!/bin/bash
# RegulensAI Database Restore Script
# Enterprise-grade database restore with safety checks and rollback capabilities

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment variables with defaults
DATABASE_URL="${DATABASE_URL:-postgresql://regulens:password@localhost:5432/regulens_training}"
S3_BUCKET="${S3_BUCKET:-regulensai-backups}"
BACKUP_PREFIX="${BACKUP_PREFIX:-training-portal}"
ENVIRONMENT="${ENVIRONMENT:-production}"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"

# Script variables
BACKUP_FILE=""
LOCAL_BACKUP_DIR="/backups"
LOG_FILE="${LOCAL_BACKUP_DIR}/restore.log"
SAFETY_BACKUP_FILE=""

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

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" | tee -a "$LOG_FILE"
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
                \"text\": \"RegulensAI Restore $status\",
                \"attachments\": [{
                    \"color\": \"$([ "$status" = "SUCCESS" ] && echo "good" || echo "danger")\",
                    \"fields\": [{
                        \"title\": \"Environment\",
                        \"value\": \"$ENVIRONMENT\",
                        \"short\": true
                    }, {
                        \"title\": \"Backup File\",
                        \"value\": \"$BACKUP_FILE\",
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
# UTILITY FUNCTIONS
# ============================================================================

show_usage() {
    echo "RegulensAI Database Restore Script"
    echo "Usage: $0 <backup_file> [options]"
    echo ""
    echo "Arguments:"
    echo "  backup_file       - Name of backup file to restore (without path)"
    echo ""
    echo "Options:"
    echo "  --list           - List available backups"
    echo "  --latest         - Restore from latest backup"
    echo "  --no-safety      - Skip safety backup creation"
    echo "  --force          - Skip confirmation prompts"
    echo "  --help           - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --latest"
    echo "  $0 training-portal_backup_20240129_143022.sql.gz"
    echo ""
    echo "Environment Variables:"
    echo "  DATABASE_URL       - PostgreSQL connection string"
    echo "  S3_BUCKET         - S3 bucket for backup storage"
    echo "  ENVIRONMENT       - Environment name"
    exit 0
}

list_available_backups() {
    log "Listing available backups from S3..."
    
    aws s3 ls "s3://$S3_BUCKET/database/$ENVIRONMENT/" \
        --recursive \
        --human-readable \
        --summarize | \
    grep "\.sql\.gz$" | \
    sort -k1,2 -r | \
    head -20
    
    echo ""
    echo "Showing latest 20 backups. Use specific filename to restore."
}

get_latest_backup() {
    aws s3 ls "s3://$S3_BUCKET/database/$ENVIRONMENT/" \
        --recursive | \
    grep "\.sql\.gz$" | \
    sort -k1,2 -r | \
    head -1 | \
    awk '{print $4}' | \
    sed "s|database/$ENVIRONMENT/||"
}

# ============================================================================
# SAFETY FUNCTIONS
# ============================================================================

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check required tools
    for tool in pg_dump pg_restore psql gunzip aws; do
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

create_safety_backup() {
    log "Creating safety backup of current database..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    SAFETY_BACKUP_FILE="$LOCAL_BACKUP_DIR/safety_backup_${timestamp}.sql"
    
    pg_dump "$DATABASE_URL" \
        --format=custom \
        --compress=6 \
        --verbose \
        --file="$SAFETY_BACKUP_FILE" \
        2>> "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Safety backup created: $SAFETY_BACKUP_FILE"
        return 0
    else
        log_error "Safety backup failed"
        return 1
    fi
}

# ============================================================================
# RESTORE FUNCTIONS
# ============================================================================

download_backup() {
    log "Downloading backup from S3..."
    
    local s3_path="s3://$S3_BUCKET/database/$ENVIRONMENT/$BACKUP_FILE"
    local local_path="$LOCAL_BACKUP_DIR/$BACKUP_FILE"
    
    if ! aws s3 ls "$s3_path" &> /dev/null; then
        log_error "Backup file not found in S3: $s3_path"
        return 1
    fi
    
    aws s3 cp "$s3_path" "$local_path" 2>> "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Backup downloaded: $local_path"
        return 0
    else
        log_error "Failed to download backup"
        return 1
    fi
}

decompress_backup() {
    log "Decompressing backup..."
    
    local compressed_path="$LOCAL_BACKUP_DIR/$BACKUP_FILE"
    local decompressed_path="${compressed_path%.gz}"
    
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gunzip "$compressed_path"
        if [[ $? -eq 0 ]]; then
            log_success "Backup decompressed"
            BACKUP_FILE=$(basename "$decompressed_path")
            return 0
        else
            log_error "Failed to decompress backup"
            return 1
        fi
    else
        log "Backup is not compressed, proceeding..."
        return 0
    fi
}

restore_database() {
    log "Restoring database..."
    log_warning "This will replace all current data!"
    
    local backup_path="$LOCAL_BACKUP_DIR/$BACKUP_FILE"
    
    # Drop existing connections
    log "Terminating existing database connections..."
    psql "$DATABASE_URL" -c "
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = current_database() AND pid <> pg_backend_pid();
    " 2>> "$LOG_FILE" || true
    
    # Restore database
    pg_restore "$backup_path" \
        --dbname="$DATABASE_URL" \
        --clean \
        --if-exists \
        --verbose \
        --single-transaction \
        2>> "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Database restore completed"
        return 0
    else
        log_error "Database restore failed"
        return 1
    fi
}

verify_restore() {
    log "Verifying restore..."
    
    # Basic connectivity test
    if ! pg_isready -d "$DATABASE_URL" -q; then
        log_error "Database is not accessible after restore"
        return 1
    fi
    
    # Check if critical tables exist
    local table_count=$(psql "$DATABASE_URL" -t -c "
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public';
    " 2>/dev/null | tr -d ' ')
    
    if [[ "$table_count" -gt 0 ]]; then
        log_success "Restore verification passed ($table_count tables found)"
        return 0
    else
        log_error "Restore verification failed (no tables found)"
        return 1
    fi
}

cleanup_files() {
    log "Cleaning up temporary files..."
    
    # Remove downloaded backup file
    rm -f "$LOCAL_BACKUP_DIR/$BACKUP_FILE"
    
    log_success "Cleanup completed"
}

# ============================================================================
# MAIN RESTORE PROCESS
# ============================================================================

main() {
    local start_time=$(date +%s)
    local success=true
    local skip_safety=false
    local force=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --list)
                list_available_backups
                exit 0
                ;;
            --latest)
                BACKUP_FILE=$(get_latest_backup)
                if [[ -z "$BACKUP_FILE" ]]; then
                    log_error "No backups found"
                    exit 1
                fi
                log "Using latest backup: $BACKUP_FILE"
                ;;
            --no-safety)
                skip_safety=true
                ;;
            --force)
                force=true
                ;;
            --help|-h)
                show_usage
                ;;
            -*)
                log_error "Unknown option: $1"
                show_usage
                ;;
            *)
                BACKUP_FILE="$1"
                ;;
        esac
        shift
    done
    
    # Validate backup file
    if [[ -z "$BACKUP_FILE" ]]; then
        log_error "No backup file specified"
        show_usage
    fi
    
    log "Starting RegulensAI database restore process"
    log "Environment: $ENVIRONMENT"
    log "Backup file: $BACKUP_FILE"
    
    # Confirmation prompt
    if [[ "$force" != true ]]; then
        echo ""
        echo "WARNING: This will replace all data in the current database!"
        echo "Database: $DATABASE_URL"
        echo "Backup: $BACKUP_FILE"
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log "Restore cancelled by user"
            exit 0
        fi
    fi
    
    # Execute restore steps
    if check_prerequisites; then
        if [[ "$skip_safety" != true ]] && ! create_safety_backup; then
            log_error "Safety backup failed, aborting restore"
            exit 1
        fi
        
        if download_backup && \
           decompress_backup && \
           restore_database && \
           verify_restore; then
            
            cleanup_files
            
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            
            log_success "Restore process completed successfully in ${duration}s"
            send_notification "SUCCESS" "Database restore completed successfully in ${duration}s"
            
        else
            success=false
            log_error "Restore process failed"
            
            if [[ -n "$SAFETY_BACKUP_FILE" ]]; then
                log "Safety backup available at: $SAFETY_BACKUP_FILE"
            fi
            
            send_notification "FAILED" "Database restore process failed. Check logs for details."
        fi
    else
        success=false
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

# Handle help request
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    show_usage
fi

# Execute main function
main "$@"
