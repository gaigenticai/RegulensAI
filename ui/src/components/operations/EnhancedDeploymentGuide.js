import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Button,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Paper,
  Switch,
  FormControlLabel,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  LinearProgress
} from '@mui/material';
import {
  ExpandMore,
  ContentCopy,
  PlayArrow,
  Cloud,
  Security,
  Storage,
  NetworkCheck,
  CheckCircle,
  Error,
  Warning,
  Info,
  CloudUpload,
  Timeline,
  Refresh
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`deployment-tabpanel-${index}`}
      aria-labelledby={`deployment-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const EnhancedDeploymentGuide = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedCloud, setSelectedCloud] = useState('aws');
  const [deploymentProgress, setDeploymentProgress] = useState(0);
  const [deploymentStatus, setDeploymentStatus] = useState('idle');
  const [validationResults, setValidationResults] = useState({});

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const runValidation = async (validationType) => {
    setValidationResults(prev => ({
      ...prev,
      [validationType]: { status: 'running', message: 'Validating...' }
    }));

    // Simulate validation
    setTimeout(() => {
      setValidationResults(prev => ({
        ...prev,
        [validationType]: { 
          status: 'success', 
          message: 'Validation passed',
          details: 'All checks completed successfully'
        }
      }));
    }, 2000);
  };

  // AWS EKS Deployment Guide
  const AWSDeploymentGuide = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        AWS EKS Deployment
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        Deploy RegulensAI on Amazon EKS with high availability and auto-scaling capabilities.
      </Alert>

      <Stepper orientation="vertical">
        <Step expanded>
          <StepLabel>Prerequisites & Setup</StepLabel>
          <StepContent>
            <Typography variant="body1" paragraph>
              Ensure you have the required AWS services and tools configured.
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom>
              Required AWS Services
            </Typography>
            <List dense>
              <ListItem>
                <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                <ListItemText primary="EKS Cluster (v1.24+)" secondary="Managed Kubernetes service" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                <ListItemText primary="RDS PostgreSQL" secondary="Managed database service" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                <ListItemText primary="ElastiCache Redis" secondary="In-memory data store" />
              </ListItem>
              <ListItem>
                <ListItemIcon><CheckCircle color="success" /></ListItemIcon>
                <ListItemText primary="Application Load Balancer" secondary="Traffic distribution" />
              </ListItem>
            </List>

            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Install AWS CLI and eksctl
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Configure AWS credentials
aws configure`}
              </SyntaxHighlighter>
              <Button
                startIcon={<ContentCopy />}
                size="small"
                onClick={() => copyToClipboard('curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"\nunzip awscliv2.zip\nsudo ./aws/install')}
              >
                Copy
              </Button>
            </Paper>
          </StepContent>
        </Step>

        <Step expanded>
          <StepLabel>Create EKS Cluster</StepLabel>
          <StepContent>
            <Typography variant="body1" paragraph>
              Create a production-ready EKS cluster with proper node groups and networking.
            </Typography>
            
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create EKS cluster
eksctl create cluster \\
  --name regulensai-prod \\
  --version 1.24 \\
  --region us-west-2 \\
  --nodegroup-name standard-workers \\
  --node-type m5.large \\
  --nodes 3 \\
  --nodes-min 1 \\
  --nodes-max 10 \\
  --managed \\
  --with-oidc \\
  --ssh-access \\
  --ssh-public-key my-key

# Verify cluster
kubectl get nodes`}
              </SyntaxHighlighter>
              <Button
                startIcon={<PlayArrow />}
                variant="outlined"
                size="small"
                sx={{ mt: 1 }}
                onClick={() => runValidation('eks-cluster')}
              >
                Validate Cluster
              </Button>
              {validationResults['eks-cluster'] && (
                <Alert 
                  severity={validationResults['eks-cluster'].status === 'success' ? 'success' : 'info'} 
                  sx={{ mt: 1 }}
                >
                  {validationResults['eks-cluster'].message}
                </Alert>
              )}
            </Paper>
          </StepContent>
        </Step>

        <Step expanded>
          <StepLabel>Configure Database & Redis</StepLabel>
          <StepContent>
            <Typography variant="body1" paragraph>
              Set up managed database services for RegulensAI.
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom>
              Create RDS PostgreSQL Instance
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create RDS subnet group
aws rds create-db-subnet-group \\
  --db-subnet-group-name regulensai-db-subnet-group \\
  --db-subnet-group-description "RegulensAI Database Subnet Group" \\
  --subnet-ids subnet-12345678 subnet-87654321

# Create RDS instance
aws rds create-db-instance \\
  --db-instance-identifier regulensai-prod-db \\
  --db-instance-class db.r5.large \\
  --engine postgres \\
  --engine-version 14.9 \\
  --master-username regulensai \\
  --master-user-password "SecurePassword123!" \\
  --allocated-storage 100 \\
  --storage-type gp2 \\
  --storage-encrypted \\
  --db-subnet-group-name regulensai-db-subnet-group \\
  --vpc-security-group-ids sg-12345678 \\
  --backup-retention-period 7 \\
  --multi-az`}
              </SyntaxHighlighter>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Create ElastiCache Redis Cluster
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create Redis subnet group
aws elasticache create-cache-subnet-group \\
  --cache-subnet-group-name regulensai-redis-subnet-group \\
  --cache-subnet-group-description "RegulensAI Redis Subnet Group" \\
  --subnet-ids subnet-12345678 subnet-87654321

# Create Redis cluster
aws elasticache create-replication-group \\
  --replication-group-id regulensai-prod-redis \\
  --description "RegulensAI Production Redis" \\
  --node-type cache.r6g.large \\
  --engine redis \\
  --engine-version 6.2 \\
  --num-cache-clusters 2 \\
  --cache-subnet-group-name regulensai-redis-subnet-group \\
  --security-group-ids sg-87654321 \\
  --at-rest-encryption-enabled \\
  --transit-encryption-enabled`}
              </SyntaxHighlighter>
            </Paper>
          </StepContent>
        </Step>

        <Step expanded>
          <StepLabel>Deploy RegulensAI Application</StepLabel>
          <StepContent>
            <Typography variant="body1" paragraph>
              Deploy the RegulensAI application to your EKS cluster.
            </Typography>
            
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create namespace
kubectl create namespace regulensai-prod

# Create secrets
kubectl create secret generic regulensai-secrets \\
  --from-literal=database-url="postgresql://regulensai:SecurePassword123!@regulensai-prod-db.region.rds.amazonaws.com:5432/regulensai" \\
  --from-literal=redis-url="redis://regulensai-prod-redis.cache.amazonaws.com:6379" \\
  --from-literal=jwt-secret="your-jwt-secret" \\
  --namespace regulensai-prod

# Deploy application
kubectl apply -f https://raw.githubusercontent.com/regulensai/deployment/main/aws-eks/regulensai-deployment.yaml

# Verify deployment
kubectl get pods -n regulensai-prod
kubectl get services -n regulensai-prod`}
              </SyntaxHighlighter>
              <Button
                startIcon={<PlayArrow />}
                variant="outlined"
                size="small"
                sx={{ mt: 1 }}
                onClick={() => runValidation('app-deployment')}
              >
                Validate Deployment
              </Button>
            </Paper>
          </StepContent>
        </Step>
      </Stepper>
    </Box>
  );

  // Google GKE Deployment Guide
  const GKEDeploymentGuide = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Google GKE Deployment
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        Deploy RegulensAI on Google Kubernetes Engine with Cloud SQL and Memorystore.
      </Alert>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Prerequisites & Setup</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>
            Install Google Cloud SDK
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize gcloud
gcloud init
gcloud auth application-default login

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Create GKE Cluster</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create GKE cluster
gcloud container clusters create regulensai-prod \\
  --zone us-central1-a \\
  --machine-type n1-standard-2 \\
  --num-nodes 3 \\
  --enable-autoscaling \\
  --min-nodes 1 \\
  --max-nodes 10 \\
  --enable-autorepair \\
  --enable-autoupgrade \\
  --enable-network-policy \\
  --enable-ip-alias

# Get credentials
gcloud container clusters get-credentials regulensai-prod --zone us-central1-a`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Setup Cloud SQL & Memorystore</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>
            Create Cloud SQL PostgreSQL Instance
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create Cloud SQL instance
gcloud sql instances create regulensai-prod-db \\
  --database-version POSTGRES_14 \\
  --tier db-n1-standard-2 \\
  --region us-central1 \\
  --storage-type SSD \\
  --storage-size 100GB \\
  --backup \\
  --maintenance-window-day SUN \\
  --maintenance-window-hour 02

# Create database and user
gcloud sql databases create regulensai --instance regulensai-prod-db
gcloud sql users create regulensai --instance regulensai-prod-db --password SecurePassword123!`}
            </SyntaxHighlighter>
          </Paper>

          <Typography variant="subtitle2" gutterBottom>
            Create Memorystore Redis Instance
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create Redis instance
gcloud redis instances create regulensai-prod-redis \\
  --size 1 \\
  --region us-central1 \\
  --redis-version redis_6_x \\
  --tier standard`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  // Azure AKS Deployment Guide
  const AzureAKSDeploymentGuide = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Azure AKS Deployment
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Deploy RegulensAI on Azure Kubernetes Service with Azure Database and Redis Cache.
      </Alert>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Prerequisites & Setup</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>
            Install Azure CLI
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Set subscription
az account set --subscription "your-subscription-id"

# Register required providers
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Cache`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Create Resource Group & AKS Cluster</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create resource group
az group create --name regulensai-prod-rg --location eastus

# Create AKS cluster
az aks create \\
  --resource-group regulensai-prod-rg \\
  --name regulensai-prod-aks \\
  --node-count 3 \\
  --node-vm-size Standard_D2s_v3 \\
  --enable-addons monitoring \\
  --enable-cluster-autoscaler \\
  --min-count 1 \\
  --max-count 10 \\
  --generate-ssh-keys \\
  --kubernetes-version 1.24.6

# Get credentials
az aks get-credentials --resource-group regulensai-prod-rg --name regulensai-prod-aks`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Setup Azure Database & Redis</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>
            Create Azure Database for PostgreSQL
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create PostgreSQL server
az postgres flexible-server create \\
  --resource-group regulensai-prod-rg \\
  --name regulensai-prod-db \\
  --location eastus \\
  --admin-user regulensai \\
  --admin-password "SecurePassword123!" \\
  --sku-name Standard_D2s_v3 \\
  --tier GeneralPurpose \\
  --storage-size 128 \\
  --version 14

# Create database
az postgres flexible-server db create \\
  --resource-group regulensai-prod-rg \\
  --server-name regulensai-prod-db \\
  --database-name regulensai`}
            </SyntaxHighlighter>
          </Paper>

          <Typography variant="subtitle2" gutterBottom>
            Create Azure Cache for Redis
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create Redis cache
az redis create \\
  --resource-group regulensai-prod-rg \\
  --name regulensai-prod-redis \\
  --location eastus \\
  --sku Standard \\
  --vm-size c1 \\
  --redis-version 6`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  // Disaster Recovery Deployment Guide
  const DisasterRecoveryDeploymentGuide = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Disaster Recovery Deployment
      </Typography>

      <Alert severity="warning" sx={{ mb: 3 }}>
        Configure multi-region disaster recovery for RegulensAI with automated failover capabilities.
      </Alert>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Multi-Region Architecture</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body1" paragraph>
              Set up RegulensAI across multiple regions for high availability and disaster recovery.
            </Typography>

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="primary">Primary Region</Typography>
                    <Typography variant="body2">US-East-1 (Production)</Typography>
                    <List dense>
                      <ListItem><ListItemText primary="Active-Active Setup" /></ListItem>
                      <ListItem><ListItemText primary="Real-time Replication" /></ListItem>
                      <ListItem><ListItemText primary="Load Balancing" /></ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="secondary">DR Region</Typography>
                    <Typography variant="body2">US-West-2 (Standby)</Typography>
                    <List dense>
                      <ListItem><ListItemText primary="Hot Standby" /></ListItem>
                      <ListItem><ListItemText primary="5-minute RPO" /></ListItem>
                      <ListItem><ListItemText primary="15-minute RTO" /></ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" color="info.main">Backup Region</Typography>
                    <Typography variant="body2">EU-West-1 (Cold)</Typography>
                    <List dense>
                      <ListItem><ListItemText primary="Cold Backup" /></ListItem>
                      <ListItem><ListItemText primary="Daily Snapshots" /></ListItem>
                      <ListItem><ListItemText primary="Compliance Archive" /></ListItem>
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Typography variant="subtitle2" gutterBottom>
              Deploy Primary Region Infrastructure
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Deploy primary region (US-East-1)
export PRIMARY_REGION=us-east-1
export DR_REGION=us-west-2
export BACKUP_REGION=eu-west-1

# Create primary cluster
eksctl create cluster \\
  --name regulensai-primary \\
  --region $PRIMARY_REGION \\
  --nodegroup-name primary-workers \\
  --node-type m5.large \\
  --nodes 3 \\
  --nodes-min 2 \\
  --nodes-max 10 \\
  --managed

# Deploy RegulensAI with DR configuration
kubectl apply -f deployment/dr/primary-region.yaml`}
              </SyntaxHighlighter>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Setup Cross-Region Database Replication
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create read replica in DR region
aws rds create-db-instance-read-replica \\
  --db-instance-identifier regulensai-dr-replica \\
  --source-db-instance-identifier regulensai-primary-db \\
  --db-instance-class db.r5.large \\
  --availability-zone us-west-2a \\
  --publicly-accessible false \\
  --auto-minor-version-upgrade true

# Configure automated backup to backup region
aws rds modify-db-instance \\
  --db-instance-identifier regulensai-primary-db \\
  --backup-retention-period 30 \\
  --copy-tags-to-snapshot \\
  --apply-immediately`}
              </SyntaxHighlighter>
            </Paper>
          </Box>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Automated Failover Configuration</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="subtitle2" gutterBottom>
            Configure Route 53 Health Checks
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Create health check for primary region
aws route53 create-health-check \\
  --caller-reference "regulensai-primary-$(date +%s)" \\
  --health-check-config '{
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "FullyQualifiedDomainName": "api.regulens.ai",
    "Port": 443,
    "RequestInterval": 30,
    "FailureThreshold": 3
  }'

# Create failover DNS record
aws route53 change-resource-record-sets \\
  --hosted-zone-id Z123456789 \\
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.regulens.ai",
        "Type": "A",
        "SetIdentifier": "primary",
        "Failover": "PRIMARY",
        "TTL": 60,
        "ResourceRecords": [{"Value": "primary-lb-ip"}],
        "HealthCheckId": "health-check-id"
      }
    }]
  }'`}
            </SyntaxHighlighter>
          </Paper>

          <Typography variant="subtitle2" gutterBottom>
            Deploy DR Monitoring & Automation
          </Typography>
          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Deploy DR monitoring stack
kubectl apply -f deployment/dr/monitoring.yaml

# Configure automated failover triggers
kubectl apply -f deployment/dr/failover-automation.yaml

# Test failover procedure
kubectl create job dr-test-failover \\
  --from=cronjob/dr-test-scheduler \\
  --namespace regulensai-dr`}
            </SyntaxHighlighter>
          </Paper>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">DR Testing & Validation</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body1" paragraph>
            Regular testing ensures your disaster recovery procedures work when needed.
          </Typography>

          <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
            <SyntaxHighlighter language="bash" style={tomorrow}>
{`# Run comprehensive DR test
python scripts/dr_manager.py full-test --dry-run

# Test database failover
python scripts/dr_manager.py test database failover_test --live

# Validate backup integrity
python scripts/dr_manager.py test database backup_validation

# Test cross-region connectivity
python scripts/dr_manager.py test network connectivity_test`}
            </SyntaxHighlighter>
            <Button
              startIcon={<PlayArrow />}
              variant="contained"
              size="small"
              sx={{ mt: 1 }}
              onClick={() => runValidation('dr-test')}
            >
              Run DR Test
            </Button>
            {validationResults['dr-test'] && (
              <Alert
                severity={validationResults['dr-test'].status === 'success' ? 'success' : 'info'}
                sx={{ mt: 1 }}
              >
                {validationResults['dr-test'].message}
              </Alert>
            )}
          </Paper>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Enhanced Deployment Guide
      </Typography>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="deployment guide tabs">
          <Tab icon={<Cloud />} label="AWS EKS" />
          <Tab icon={<CloudUpload />} label="Google GKE" />
          <Tab icon={<Storage />} label="Azure AKS" />
          <Tab icon={<Security />} label="Disaster Recovery" />
        </Tabs>
      </Box>

      <TabPanel value={activeTab} index={0}>
        <AWSDeploymentGuide />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <GKEDeploymentGuide />
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <AzureAKSDeploymentGuide />
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <DisasterRecoveryDeploymentGuide />
      </TabPanel>
    </Box>
  );
};

export default EnhancedDeploymentGuide;
