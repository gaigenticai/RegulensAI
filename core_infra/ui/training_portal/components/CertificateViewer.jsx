import React, { useState, useRef } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Avatar,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  TextField,
  InputAdornment,
  Tooltip,
  Alert,
  CircularProgress
} from '@mui/material';
import {
  Certificate,
  Download,
  Print,
  Share,
  Verified,
  Search,
  FilterList,
  Star,
  School,
  CalendarToday,
  Person,
  QrCode,
  Email,
  LinkedIn,
  Twitter,
  Facebook,
  Link as LinkIcon
} from '@mui/icons-material';
import { QRCodeSVG } from 'qrcode.react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { TrainingAPI } from '../../services/TrainingAPI';

const CertificateViewer = ({ certificates, onRefresh }) => {
  const [selectedCertificate, setSelectedCertificate] = useState(null);
  const [showCertificateDialog, setShowCertificateDialog] = useState(false);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [downloading, setDownloading] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  
  const certificateRef = useRef(null);

  // Filter certificates based on search and type
  const filteredCertificates = certificates.filter(cert => {
    const matchesSearch = cert.module_title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         cert.certificate_number?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'all' || cert.certificate_type === filterType;
    return matchesSearch && matchesType;
  });

  const handleViewCertificate = (certificate) => {
    setSelectedCertificate(certificate);
    setShowCertificateDialog(true);
  };

  const handleDownloadCertificate = async (certificate, format = 'pdf') => {
    try {
      setDownloading(true);
      
      if (format === 'pdf') {
        // Generate PDF from certificate component
        const canvas = await html2canvas(certificateRef.current, {
          scale: 2,
          useCORS: true,
          allowTaint: true
        });
        
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('landscape', 'mm', 'a4');
        const imgWidth = 297;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        pdf.addImage(imgData, 'PNG', 0, 0, imgWidth, imgHeight);
        pdf.save(`certificate-${certificate.certificate_number}.pdf`);
      } else {
        // Download from API
        const blob = await TrainingAPI.downloadCertificate(certificate.id, format);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `certificate-${certificate.certificate_number}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Failed to download certificate:', error);
    } finally {
      setDownloading(false);
    }
  };

  const handlePrintCertificate = () => {
    window.print();
  };

  const handleShareCertificate = (certificate) => {
    setSelectedCertificate(certificate);
    setShowShareDialog(true);
  };

  const handleSocialShare = (platform, certificate) => {
    const certificateUrl = `${window.location.origin}/certificates/verify/${certificate.verification_code}`;
    const text = `I've completed ${certificate.module_title} training and earned my certificate from RegulensAI!`;
    
    let shareUrl = '';
    
    switch (platform) {
      case 'linkedin':
        shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(certificateUrl)}&title=${encodeURIComponent(text)}`;
        break;
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(certificateUrl)}`;
        break;
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(certificateUrl)}`;
        break;
      default:
        // Copy to clipboard
        navigator.clipboard.writeText(certificateUrl);
        return;
    }
    
    window.open(shareUrl, '_blank', 'width=600,height=400');
  };

  const handleVerifyCertificate = async () => {
    if (!verificationCode.trim()) return;
    
    try {
      setVerifying(true);
      const result = await TrainingAPI.verifyCertificate(verificationCode);
      setVerificationResult(result);
    } catch (error) {
      setVerificationResult({ valid: false, error: 'Certificate not found or invalid' });
    } finally {
      setVerifying(false);
    }
  };

  const renderCertificateCard = (certificate) => {
    const isExpired = certificate.expires_at && new Date(certificate.expires_at) < new Date();
    
    return (
      <Card 
        key={certificate.id}
        sx={{ 
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          opacity: isExpired ? 0.7 : 1
        }}
      >
        {/* Certificate Type Badge */}
        <Chip
          icon={<Certificate />}
          label={certificate.certificate_type}
          color={certificate.certificate_type === 'mastery' ? 'secondary' : 'primary'}
          size="small"
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 1
          }}
        />
        
        <CardContent sx={{ flexGrow: 1, pt: 5 }}>
          {/* Certificate Header */}
          <Box display="flex" alignItems="center" mb={2}>
            <Avatar 
              sx={{ 
                bgcolor: 'primary.main',
                width: 56,
                height: 56,
                mr: 2
              }}
            >
              <School fontSize="large" />
            </Avatar>
            
            <Box flexGrow={1}>
              <Typography variant="h6" gutterBottom>
                {certificate.module_title}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Certificate #{certificate.certificate_number}
              </Typography>
            </Box>
          </Box>

          {/* Certificate Details */}
          <Box mb={2}>
            <Box display="flex" alignItems="center" mb={1}>
              <CalendarToday fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
              <Typography variant="body2" color="textSecondary">
                Issued: {new Date(certificate.issued_at).toLocaleDateString()}
              </Typography>
            </Box>
            
            {certificate.expires_at && (
              <Box display="flex" alignItems="center" mb={1}>
                <CalendarToday fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography 
                  variant="body2" 
                  color={isExpired ? 'error' : 'textSecondary'}
                >
                  Expires: {new Date(certificate.expires_at).toLocaleDateString()}
                  {isExpired && ' (Expired)'}
                </Typography>
              </Box>
            )}
            
            {certificate.final_score && (
              <Box display="flex" alignItems="center" mb={1}>
                <Star fontSize="small" sx={{ mr: 1, color: 'warning.main' }} />
                <Typography variant="body2" color="textSecondary">
                  Final Score: {certificate.final_score}%
                </Typography>
              </Box>
            )}
          </Box>

          {/* Verification Status */}
          <Box display="flex" alignItems="center" mb={2}>
            <Verified 
              color={certificate.is_valid ? 'success' : 'error'} 
              fontSize="small" 
              sx={{ mr: 1 }} 
            />
            <Typography 
              variant="body2" 
              color={certificate.is_valid ? 'success.main' : 'error.main'}
            >
              {certificate.is_valid ? 'Verified' : 'Invalid'}
            </Typography>
          </Box>
        </CardContent>

        {/* Actions */}
        <Box sx={{ p: 2, pt: 0 }}>
          <Box display="flex" gap={1} flexWrap="wrap">
            <Button
              size="small"
              variant="contained"
              startIcon={<Certificate />}
              onClick={() => handleViewCertificate(certificate)}
            >
              View
            </Button>
            
            <Button
              size="small"
              variant="outlined"
              startIcon={<Download />}
              onClick={() => handleDownloadCertificate(certificate)}
              disabled={downloading}
            >
              Download
            </Button>
            
            <Button
              size="small"
              variant="outlined"
              startIcon={<Share />}
              onClick={() => handleShareCertificate(certificate)}
            >
              Share
            </Button>
          </Box>
        </Box>
      </Card>
    );
  };

  const renderCertificateDisplay = (certificate) => (
    <Paper 
      ref={certificateRef}
      sx={{ 
        p: 4, 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        textAlign: 'center',
        minHeight: '400px',
        position: 'relative'
      }}
    >
      {/* Decorative Border */}
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          left: 16,
          right: 16,
          bottom: 16,
          border: '3px solid rgba(255,255,255,0.3)',
          borderRadius: 2
        }}
      />
      
      {/* Certificate Content */}
      <Box sx={{ position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
          Certificate of Completion
        </Typography>
        
        <Typography variant="h6" sx={{ mb: 4, opacity: 0.9 }}>
          RegulensAI Training Program
        </Typography>
        
        {/* Recipient */}
        <Typography variant="h5" sx={{ mb: 2 }}>
          This certifies that
        </Typography>
        
        <Typography variant="h4" sx={{ fontWeight: 'bold', mb: 4, textDecoration: 'underline' }}>
          {certificate.user_name || 'Certificate Holder'}
        </Typography>
        
        {/* Achievement */}
        <Typography variant="h6" sx={{ mb: 2 }}>
          has successfully completed the training module
        </Typography>
        
        <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 4 }}>
          {certificate.module_title}
        </Typography>
        
        {/* Details */}
        <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mt: 6 }}>
          <Box textAlign="left">
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Certificate Number
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
              {certificate.certificate_number}
            </Typography>
          </Box>
          
          <Box textAlign="center">
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Date Issued
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
              {new Date(certificate.issued_at).toLocaleDateString()}
            </Typography>
          </Box>
          
          <Box textAlign="right">
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Final Score
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 'bold' }}>
              {certificate.final_score}%
            </Typography>
          </Box>
        </Box>
        
        {/* QR Code for Verification */}
        <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
          <Box sx={{ bgcolor: 'white', p: 1, borderRadius: 1 }}>
            <QRCodeSVG
              value={`${window.location.origin}/certificates/verify/${certificate.verification_code}`}
              size={80}
            />
          </Box>
        </Box>
        
        <Typography variant="caption" sx={{ mt: 1, display: 'block', opacity: 0.8 }}>
          Scan to verify certificate authenticity
        </Typography>
      </Box>
    </Paper>
  );

  return (
    <Box>
      {/* Header and Controls */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" gutterBottom>
          My Certificates
        </Typography>
        
        <Box display="flex" gap={2}>
          <TextField
            size="small"
            placeholder="Search certificates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              )
            }}
          />
          
          <Button
            variant="outlined"
            startIcon={<FilterList />}
            onClick={() => {/* Filter dialog */}}
          >
            Filter
          </Button>
        </Box>
      </Box>

      {/* Certificate Verification */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Verify Certificate
        </Typography>
        <Box display="flex" gap={2} alignItems="center">
          <TextField
            size="small"
            placeholder="Enter verification code..."
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
            sx={{ flexGrow: 1 }}
          />
          <Button
            variant="contained"
            onClick={handleVerifyCertificate}
            disabled={verifying || !verificationCode.trim()}
          >
            {verifying ? <CircularProgress size={20} /> : 'Verify'}
          </Button>
        </Box>
        
        {verificationResult && (
          <Alert 
            severity={verificationResult.valid ? 'success' : 'error'}
            sx={{ mt: 2 }}
          >
            {verificationResult.valid 
              ? `Certificate is valid for ${verificationResult.module_title}`
              : verificationResult.error || 'Certificate is not valid'
            }
          </Alert>
        )}
      </Paper>

      {/* Certificates Grid */}
      {filteredCertificates.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <School sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="textSecondary" gutterBottom>
            No certificates found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Complete training modules to earn certificates
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {filteredCertificates.map(certificate => (
            <Grid item xs={12} md={6} lg={4} key={certificate.id}>
              {renderCertificateCard(certificate)}
            </Grid>
          ))}
        </Grid>
      )}

      {/* Certificate Display Dialog */}
      <Dialog
        open={showCertificateDialog}
        onClose={() => setShowCertificateDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Certificate Details</Typography>
            <Box>
              <IconButton onClick={handlePrintCertificate}>
                <Print />
              </IconButton>
              <IconButton onClick={() => handleDownloadCertificate(selectedCertificate)}>
                <Download />
              </IconButton>
            </Box>
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedCertificate && renderCertificateDisplay(selectedCertificate)}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setShowCertificateDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Share Dialog */}
      <Dialog
        open={showShareDialog}
        onClose={() => setShowShareDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Share Certificate</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Share your achievement on social media or copy the verification link.
          </Typography>
          
          <Box display="flex" gap={2} justifyContent="center" my={3}>
            <Button
              variant="outlined"
              startIcon={<LinkedIn />}
              onClick={() => handleSocialShare('linkedin', selectedCertificate)}
            >
              LinkedIn
            </Button>
            <Button
              variant="outlined"
              startIcon={<Twitter />}
              onClick={() => handleSocialShare('twitter', selectedCertificate)}
            >
              Twitter
            </Button>
            <Button
              variant="outlined"
              startIcon={<Facebook />}
              onClick={() => handleSocialShare('facebook', selectedCertificate)}
            >
              Facebook
            </Button>
          </Box>
          
          <TextField
            fullWidth
            label="Verification Link"
            value={selectedCertificate ? `${window.location.origin}/certificates/verify/${selectedCertificate.verification_code}` : ''}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={() => handleSocialShare('copy', selectedCertificate)}>
                    <LinkIcon />
                  </IconButton>
                </InputAdornment>
              )
            }}
          />
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setShowShareDialog(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CertificateViewer;
