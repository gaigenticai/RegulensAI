//! Cache Compression

use crate::{config::CompressionConfig, errors::{CacheError, CacheResult}};
use std::io::{Read, Write};

/// Cache compressor with advanced compression algorithms
pub struct CacheCompressor {
    config: CompressionConfig,
    compression_stats: CompressionStats,
}

/// Compression algorithm
pub use crate::config::CompressionAlgorithm;

/// Compression statistics
#[derive(Debug, Clone, Default)]
pub struct CompressionStats {
    pub total_compressions: u64,
    pub total_decompressions: u64,
    pub bytes_compressed: u64,
    pub bytes_decompressed: u64,
    pub compression_ratio: f64,
    pub average_compression_time_ms: f64,
    pub average_decompression_time_ms: f64,
}

impl CacheCompressor {
    pub fn new(config: CompressionConfig) -> Self {
        Self {
            config,
            compression_stats: CompressionStats::default(),
        }
    }

    /// Compress data using the configured algorithm
    pub fn compress(&mut self, data: &[u8]) -> CacheResult<Vec<u8>> {
        let start_time = std::time::Instant::now();

        if data.len() < self.config.threshold_bytes {
            return Ok(data.to_vec());
        }

        let result = match self.config.algorithm {
            CompressionAlgorithm::None => Ok(data.to_vec()),
            CompressionAlgorithm::Lz4 => self.compress_lz4(data),
            CompressionAlgorithm::Zstd => self.compress_zstd(data),
            CompressionAlgorithm::Gzip => self.compress_gzip(data),
        };

        // Update statistics
        let compression_time = start_time.elapsed().as_millis() as f64;
        self.update_compression_stats(data.len(), result.as_ref().map(|r| r.len()).unwrap_or(0), compression_time);

        result
    }

    /// Decompress data using the configured algorithm
    pub fn decompress(&mut self, data: &[u8]) -> CacheResult<Vec<u8>> {
        let start_time = std::time::Instant::now();

        let result = match self.config.algorithm {
            CompressionAlgorithm::None => Ok(data.to_vec()),
            CompressionAlgorithm::Lz4 => self.decompress_lz4(data),
            CompressionAlgorithm::Zstd => self.decompress_zstd(data),
            CompressionAlgorithm::Gzip => self.decompress_gzip(data),
        };

        // Update statistics
        let decompression_time = start_time.elapsed().as_millis() as f64;
        self.update_decompression_stats(data.len(), result.as_ref().map(|r| r.len()).unwrap_or(0), decompression_time);

        result
    }

    /// Compress using LZ4 algorithm
    fn compress_lz4(&self, data: &[u8]) -> CacheResult<Vec<u8>> {
        // Add compression level support for LZ4
        let compressed = if self.config.level <= 1 {
            lz4_flex::compress_prepend_size(data)
        } else {
            // Use high compression mode for levels > 1
            let mut compressed = Vec::new();
            let original_len = data.len() as u32;
            compressed.extend_from_slice(&original_len.to_le_bytes());

            let compressed_data = lz4_flex::compress(data);
            compressed.extend_from_slice(&compressed_data);
            compressed
        };

        Ok(compressed)
    }

    /// Decompress using LZ4 algorithm
    fn decompress_lz4(&self, data: &[u8]) -> CacheResult<Vec<u8>> {
        if data.len() < 4 {
            return Err(CacheError::Compression("Invalid LZ4 compressed data".to_string()));
        }

        // Check if it's size-prepended format
        if data.len() >= 8 {
            // Try size-prepended decompression first
            if let Ok(decompressed) = lz4_flex::decompress_size_prepended(data) {
                return Ok(decompressed);
            }
        }

        // Fall back to manual decompression
        let original_len = u32::from_le_bytes([data[0], data[1], data[2], data[3]]) as usize;
        let compressed_data = &data[4..];

        let decompressed = lz4_flex::decompress(compressed_data, original_len)
            .map_err(|e| CacheError::Compression(format!("LZ4 decompression failed: {}", e)))?;

        Ok(decompressed)
    }

    /// Compress using Zstandard algorithm
    fn compress_zstd(&self, data: &[u8]) -> CacheResult<Vec<u8>> {
        let level = self.config.level.clamp(1, 22) as i32; // Zstd supports levels 1-22
        zstd::encode_all(data, level)
            .map_err(|e| CacheError::Compression(format!("Zstd compression failed: {}", e)))
    }

    /// Decompress using Zstandard algorithm
    fn decompress_zstd(&self, data: &[u8]) -> CacheResult<Vec<u8>> {
        zstd::decode_all(data)
            .map_err(|e| CacheError::Compression(format!("Zstd decompression failed: {}", e)))
    }

    /// Compress using Gzip algorithm
    fn compress_gzip(&self, data: &[u8]) -> CacheResult<Vec<u8>> {
        let mut encoder = flate2::write::GzEncoder::new(
            Vec::new(),
            flate2::Compression::new(self.config.level.clamp(0, 9))
        );

        encoder.write_all(data)
            .map_err(|e| CacheError::Compression(format!("Gzip write failed: {}", e)))?;

        encoder.finish()
            .map_err(|e| CacheError::Compression(format!("Gzip compression failed: {}", e)))
    }

    /// Decompress using Gzip algorithm
    fn decompress_gzip(&self, data: &[u8]) -> CacheResult<Vec<u8>> {
        let mut decoder = flate2::read::GzDecoder::new(data);
        let mut decompressed = Vec::new();

        decoder.read_to_end(&mut decompressed)
            .map_err(|e| CacheError::Compression(format!("Gzip decompression failed: {}", e)))?;

        Ok(decompressed)
    }

    /// Update compression statistics
    fn update_compression_stats(&mut self, original_size: usize, compressed_size: usize, time_ms: f64) {
        self.compression_stats.total_compressions += 1;
        self.compression_stats.bytes_compressed += original_size as u64;

        // Update average compression time
        let total_compressions = self.compression_stats.total_compressions as f64;
        self.compression_stats.average_compression_time_ms =
            (self.compression_stats.average_compression_time_ms * (total_compressions - 1.0) + time_ms) / total_compressions;

        // Update compression ratio
        if original_size > 0 {
            let current_ratio = compressed_size as f64 / original_size as f64;
            self.compression_stats.compression_ratio =
                (self.compression_stats.compression_ratio * (total_compressions - 1.0) + current_ratio) / total_compressions;
        }
    }

    /// Update decompression statistics
    fn update_decompression_stats(&mut self, compressed_size: usize, decompressed_size: usize, time_ms: f64) {
        self.compression_stats.total_decompressions += 1;
        self.compression_stats.bytes_decompressed += decompressed_size as u64;

        // Update average decompression time
        let total_decompressions = self.compression_stats.total_decompressions as f64;
        self.compression_stats.average_decompression_time_ms =
            (self.compression_stats.average_decompression_time_ms * (total_decompressions - 1.0) + time_ms) / total_decompressions;
    }

    /// Get compression statistics
    pub fn get_stats(&self) -> &CompressionStats {
        &self.compression_stats
    }

    /// Reset compression statistics
    pub fn reset_stats(&mut self) {
        self.compression_stats = CompressionStats::default();
    }

    /// Calculate compression efficiency for given data
    pub fn calculate_efficiency(&mut self, data: &[u8]) -> CacheResult<CompressionEfficiency> {
        let original_size = data.len();
        let compressed = self.compress(data)?;
        let compressed_size = compressed.len();

        let compression_ratio = if original_size > 0 {
            compressed_size as f64 / original_size as f64
        } else {
            1.0
        };

        let space_saved = original_size.saturating_sub(compressed_size);
        let space_saved_percentage = if original_size > 0 {
            (space_saved as f64 / original_size as f64) * 100.0
        } else {
            0.0
        };

        Ok(CompressionEfficiency {
            original_size,
            compressed_size,
            compression_ratio,
            space_saved,
            space_saved_percentage,
            algorithm: self.config.algorithm.clone(),
            compression_level: self.config.level,
        })
    }
}

/// Compression efficiency metrics
#[derive(Debug, Clone)]
pub struct CompressionEfficiency {
    pub original_size: usize,
    pub compressed_size: usize,
    pub compression_ratio: f64,
    pub space_saved: usize,
    pub space_saved_percentage: f64,
    pub algorithm: CompressionAlgorithm,
    pub compression_level: u32,
}
