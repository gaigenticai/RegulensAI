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
  FormControlLabel
} from '@mui/material';
import {
  ExpandMore,
  ContentCopy,
  PlayArrow,
  Security,
  Code,
  Api,
  Webhook,
  Speed,
  Language,
  CheckCircle,
  Error,
  Warning,
  Info
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`api-tabpanel-${index}`}
      aria-labelledby={`api-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const EnhancedAPIDocumentation = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState('python');
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [webhookTestOpen, setWebhookTestOpen] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const testApiEndpoint = async (endpoint, method, payload) => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setApiResponse({
        status: 200,
        data: { message: 'API call successful', endpoint, method }
      });
    } catch (error) {
      setApiResponse({
        status: 500,
        error: error.message
      });
    } finally {
      setLoading(false);
    }
  };

  // OAuth2/SAML Authentication Examples
  const AuthenticationExamples = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Authentication Flows
      </Typography>
      
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">OAuth2 Authorization Code Flow</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body1" paragraph>
              RegulensAI supports OAuth2 authorization code flow for secure third-party integrations.
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom>
              Step 1: Authorization Request
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" component="pre" sx={{ flex: 1, overflow: 'auto' }}>
{`GET /oauth/authorize?
  response_type=code&
  client_id=your_client_id&
  redirect_uri=https://yourapp.com/callback&
  scope=read:regulations write:compliance&
  state=random_state_string`}
                </Typography>
                <Tooltip title="Copy to clipboard">
                  <IconButton onClick={() => copyToClipboard(`GET /oauth/authorize?response_type=code&client_id=your_client_id&redirect_uri=https://yourapp.com/callback&scope=read:regulations write:compliance&state=random_state_string`)}>
                    <ContentCopy />
                  </IconButton>
                </Tooltip>
              </Box>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Step 2: Token Exchange
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`curl -X POST https://api.regulens.ai/oauth/token \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=authorization_code" \\
  -d "code=AUTH_CODE_HERE" \\
  -d "redirect_uri=https://yourapp.com/callback" \\
  -d "client_id=your_client_id" \\
  -d "client_secret=your_client_secret"`}
              </SyntaxHighlighter>
              <Button
                startIcon={<ContentCopy />}
                size="small"
                onClick={() => copyToClipboard(`curl -X POST https://api.regulens.ai/oauth/token -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=authorization_code" -d "code=AUTH_CODE_HERE" -d "redirect_uri=https://yourapp.com/callback" -d "client_id=your_client_id" -d "client_secret=your_client_secret"`)}
              >
                Copy
              </Button>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Step 3: Using Access Token
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`curl -X GET https://api.regulens.ai/v1/regulations \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json"`}
              </SyntaxHighlighter>
            </Paper>
          </Box>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">SAML SSO Integration</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="body1" paragraph>
              Enterprise SAML SSO integration for seamless authentication.
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom>
              SAML Configuration
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="xml" style={tomorrow}>
{`<saml:Issuer>https://api.regulens.ai</saml:Issuer>
<saml:NameIDPolicy Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"/>
<saml:AuthnContextClassRef>
  urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
</saml:AuthnContextClassRef>`}
              </SyntaxHighlighter>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Assertion Validation
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="python" style={tomorrow}>
{`from regulensai import SAMLAuth

# Initialize SAML authentication
saml_auth = SAMLAuth(
    entity_id="https://api.regulens.ai",
    sso_url="https://your-idp.com/sso",
    x509_cert="YOUR_CERTIFICATE"
)

# Validate SAML response
user_info = saml_auth.validate_response(saml_response)
access_token = saml_auth.get_access_token(user_info)`}
              </SyntaxHighlighter>
            </Paper>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  // Rate Limiting Documentation
  const RateLimitingDocs = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Rate Limiting & Quotas
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3 }}>
        RegulensAI implements intelligent rate limiting to ensure fair usage and optimal performance for all users.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Rate Limits by Plan
              </Typography>
              <List>
                <ListItem>
                  <ListItemIcon><Chip label="Free" color="default" size="small" /></ListItemIcon>
                  <ListItemText primary="100 requests/hour" secondary="Basic endpoints only" />
                </ListItem>
                <ListItem>
                  <ListItemIcon><Chip label="Pro" color="primary" size="small" /></ListItemIcon>
                  <ListItemText primary="1,000 requests/hour" secondary="All endpoints" />
                </ListItem>
                <ListItem>
                  <ListItemIcon><Chip label="Enterprise" color="secondary" size="small" /></ListItemIcon>
                  <ListItemText primary="10,000 requests/hour" secondary="Priority support" />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Rate Limit Headers
              </Typography>
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <SyntaxHighlighter language="http" style={tomorrow}>
{`HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
Retry-After: 3600`}
                </SyntaxHighlighter>
              </Paper>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box mt={3}>
        <Typography variant="h6" gutterBottom>
          Handling Rate Limits
        </Typography>
        <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
          <SyntaxHighlighter language="python" style={tomorrow}>
{`import time
import requests
from regulensai import RegulensAIClient

client = RegulensAIClient(api_key="your_api_key")

def make_request_with_retry(endpoint, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.get(endpoint)
            return response
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = int(e.retry_after)
                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    
# Usage
regulations = make_request_with_retry("/v1/regulations")`}
          </SyntaxHighlighter>
        </Paper>
      </Box>
    </Box>
  );

  // Webhook Documentation
  const WebhookDocs = () => (
    <Box>
      <Typography variant="h5" gutterBottom>
        Webhooks & Event Notifications
      </Typography>
      
      <Typography variant="body1" paragraph>
        RegulensAI can send real-time notifications to your application when important events occur.
      </Typography>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Webhook Configuration</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Create Webhook Endpoint
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="bash" style={tomorrow}>
{`curl -X POST https://api.regulens.ai/v1/webhooks \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://yourapp.com/webhooks/regulensai",
    "events": ["regulation.updated", "compliance.alert", "report.generated"],
    "secret": "your_webhook_secret"
  }'`}
              </SyntaxHighlighter>
              <Button
                startIcon={<PlayArrow />}
                variant="outlined"
                size="small"
                sx={{ mt: 1 }}
                onClick={() => setWebhookTestOpen(true)}
              >
                Test Webhook
              </Button>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Webhook Payload Example
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="json" style={tomorrow}>
{`{
  "id": "evt_1234567890",
  "type": "regulation.updated",
  "created": "2024-01-15T10:30:00Z",
  "data": {
    "regulation_id": "reg_abc123",
    "title": "Updated MiFID II Requirements",
    "changes": ["section_3", "appendix_a"],
    "effective_date": "2024-02-01T00:00:00Z"
  },
  "signature": "sha256=a1b2c3d4e5f6..."
}`}
              </SyntaxHighlighter>
            </Paper>

            <Typography variant="subtitle2" gutterBottom>
              Signature Verification
            </Typography>
            <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
              <SyntaxHighlighter language="python" style={tomorrow}>
{`import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(
        f"sha256={expected_signature}",
        signature
    )`}
              </SyntaxHighlighter>
            </Paper>
          </Box>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Available Events</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List>
            <ListItem>
              <ListItemIcon><Chip label="regulation.created" color="success" size="small" /></ListItemIcon>
              <ListItemText primary="New regulation added" secondary="Triggered when a new regulation is published" />
            </ListItem>
            <ListItem>
              <ListItemIcon><Chip label="regulation.updated" color="warning" size="small" /></ListItemIcon>
              <ListItemText primary="Regulation modified" secondary="Triggered when existing regulation is updated" />
            </ListItem>
            <ListItem>
              <ListItemIcon><Chip label="compliance.alert" color="error" size="small" /></ListItemIcon>
              <ListItemText primary="Compliance violation detected" secondary="Triggered when compliance issues are identified" />
            </ListItem>
            <ListItem>
              <ListItemIcon><Chip label="report.generated" color="info" size="small" /></ListItemIcon>
              <ListItemText primary="Report ready for download" secondary="Triggered when scheduled reports are completed" />
            </ListItem>
          </List>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  // SDK Examples Component
  const SDKExamples = ({ selectedLanguage, setSelectedLanguage }) => (
    <Box>
      <Typography variant="h5" gutterBottom>
        SDK & Client Library Examples
      </Typography>

      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Language</InputLabel>
          <Select
            value={selectedLanguage}
            label="Language"
            onChange={(e) => setSelectedLanguage(e.target.value)}
          >
            <MenuItem value="python">Python</MenuItem>
            <MenuItem value="javascript">JavaScript</MenuItem>
            <MenuItem value="java">Java</MenuItem>
            <MenuItem value="csharp">C#</MenuItem>
            <MenuItem value="php">PHP</MenuItem>
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary">
          Choose your preferred programming language
        </Typography>
      </Box>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Installation & Setup</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            {selectedLanguage === 'python' && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Install via pip</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="bash" style={tomorrow}>
                    {`pip install regulensai-python`}
                  </SyntaxHighlighter>
                </Paper>
                <Typography variant="subtitle2" gutterBottom>Basic Setup</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="python" style={tomorrow}>
{`from regulensai import RegulensAIClient

# Initialize client
client = RegulensAIClient(
    api_key="your_api_key",
    base_url="https://api.regulens.ai/v1"
)

# Test connection
health = client.health_check()
print(f"API Status: {health.status}")`}
                  </SyntaxHighlighter>
                </Paper>
              </Box>
            )}

            {selectedLanguage === 'javascript' && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Install via npm</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="bash" style={tomorrow}>
                    {`npm install @regulensai/sdk`}
                  </SyntaxHighlighter>
                </Paper>
                <Typography variant="subtitle2" gutterBottom>Basic Setup</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="javascript" style={tomorrow}>
{`import { RegulensAIClient } from '@regulensai/sdk';

// Initialize client
const client = new RegulensAIClient({
  apiKey: 'your_api_key',
  baseURL: 'https://api.regulens.ai/v1'
});

// Test connection
const health = await client.healthCheck();
console.log(\`API Status: \${health.status}\`);`}
                  </SyntaxHighlighter>
                </Paper>
              </Box>
            )}

            {selectedLanguage === 'java' && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Maven Dependency</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="xml" style={tomorrow}>
{`<dependency>
    <groupId>ai.regulens</groupId>
    <artifactId>regulensai-java</artifactId>
    <version>1.0.0</version>
</dependency>`}
                  </SyntaxHighlighter>
                </Paper>
                <Typography variant="subtitle2" gutterBottom>Basic Setup</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="java" style={tomorrow}>
{`import ai.regulens.RegulensAIClient;
import ai.regulens.models.HealthCheck;

// Initialize client
RegulensAIClient client = new RegulensAIClient.Builder()
    .apiKey("your_api_key")
    .baseUrl("https://api.regulens.ai/v1")
    .build();

// Test connection
HealthCheck health = client.healthCheck();
System.out.println("API Status: " + health.getStatus());`}
                  </SyntaxHighlighter>
                </Paper>
              </Box>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Common Operations</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            {selectedLanguage === 'python' && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Fetch Regulations</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="python" style={tomorrow}>
{`# Get all regulations
regulations = client.regulations.list(
    jurisdiction="US",
    category="banking",
    limit=50
)

# Get specific regulation
regulation = client.regulations.get("reg_123")
print(f"Title: {regulation.title}")
print(f"Status: {regulation.status}")

# Search regulations
results = client.regulations.search(
    query="capital requirements",
    filters={"effective_date": "2024-01-01"}
)`}
                  </SyntaxHighlighter>
                </Paper>

                <Typography variant="subtitle2" gutterBottom>Compliance Monitoring</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="python" style={tomorrow}>
{`# Check compliance status
compliance = client.compliance.check(
    entity_id="entity_123",
    regulation_ids=["reg_123", "reg_456"]
)

# Get compliance alerts
alerts = client.compliance.alerts(
    severity="high",
    status="open",
    date_range={"start": "2024-01-01", "end": "2024-01-31"}
)

# Generate compliance report
report = client.reports.generate(
    type="compliance_summary",
    entities=["entity_123"],
    regulations=["reg_123"]
)`}
                  </SyntaxHighlighter>
                </Paper>
              </Box>
            )}

            {selectedLanguage === 'javascript' && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>Fetch Regulations</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="javascript" style={tomorrow}>
{`// Get all regulations
const regulations = await client.regulations.list({
  jurisdiction: 'US',
  category: 'banking',
  limit: 50
});

// Get specific regulation
const regulation = await client.regulations.get('reg_123');
console.log(\`Title: \${regulation.title}\`);
console.log(\`Status: \${regulation.status}\`);

// Search regulations
const results = await client.regulations.search({
  query: 'capital requirements',
  filters: { effective_date: '2024-01-01' }
});`}
                  </SyntaxHighlighter>
                </Paper>

                <Typography variant="subtitle2" gutterBottom>Compliance Monitoring</Typography>
                <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
                  <SyntaxHighlighter language="javascript" style={tomorrow}>
{`// Check compliance status
const compliance = await client.compliance.check({
  entityId: 'entity_123',
  regulationIds: ['reg_123', 'reg_456']
});

// Get compliance alerts
const alerts = await client.compliance.alerts({
  severity: 'high',
  status: 'open',
  dateRange: { start: '2024-01-01', end: '2024-01-31' }
});

// Generate compliance report
const report = await client.reports.generate({
  type: 'compliance_summary',
  entities: ['entity_123'],
  regulations: ['reg_123']
});`}
                  </SyntaxHighlighter>
                </Paper>
              </Box>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography variant="h6">Error Handling</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box>
            {selectedLanguage === 'python' && (
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <SyntaxHighlighter language="python" style={tomorrow}>
{`from regulensai.exceptions import (
    RegulensAIError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)

try:
    regulations = client.regulations.list()
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after}")
except ValidationError as e:
    print(f"Validation error: {e.details}")
except RegulensAIError as e:
    print(f"API error: {e.message}")
    print(f"Status code: {e.status_code}")
    print(f"Request ID: {e.request_id}")`}
                </SyntaxHighlighter>
              </Paper>
            )}

            {selectedLanguage === 'javascript' && (
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <SyntaxHighlighter language="javascript" style={tomorrow}>
{`import {
  RegulensAIError,
  AuthenticationError,
  RateLimitError,
  ValidationError
} from '@regulensai/sdk';

try {
  const regulations = await client.regulations.list();
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log(\`Authentication failed: \${error.message}\`);
  } else if (error instanceof RateLimitError) {
    console.log(\`Rate limit exceeded. Retry after: \${error.retryAfter}\`);
  } else if (error instanceof ValidationError) {
    console.log(\`Validation error: \${error.details}\`);
  } else if (error instanceof RegulensAIError) {
    console.log(\`API error: \${error.message}\`);
    console.log(\`Status code: \${error.statusCode}\`);
    console.log(\`Request ID: \${error.requestId}\`);
  }
}`}
                </SyntaxHighlighter>
              </Paper>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Enhanced API Documentation
      </Typography>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={handleTabChange} aria-label="API documentation tabs">
          <Tab icon={<Security />} label="Authentication" />
          <Tab icon={<Speed />} label="Rate Limiting" />
          <Tab icon={<Webhook />} label="Webhooks" />
          <Tab icon={<Language />} label="SDK Examples" />
        </Tabs>
      </Box>

      <TabPanel value={activeTab} index={0}>
        <AuthenticationExamples />
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <RateLimitingDocs />
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        <WebhookDocs />
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        <SDKExamples selectedLanguage={selectedLanguage} setSelectedLanguage={setSelectedLanguage} />
      </TabPanel>

      {/* Webhook Test Dialog */}
      <Dialog open={webhookTestOpen} onClose={() => setWebhookTestOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Test Webhook Endpoint</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Webhook URL"
            placeholder="https://yourapp.com/webhooks/regulensai"
            margin="normal"
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Event Type</InputLabel>
            <Select defaultValue="regulation.updated">
              <MenuItem value="regulation.created">regulation.created</MenuItem>
              <MenuItem value="regulation.updated">regulation.updated</MenuItem>
              <MenuItem value="compliance.alert">compliance.alert</MenuItem>
              <MenuItem value="report.generated">report.generated</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWebhookTestOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => setWebhookTestOpen(false)}>Send Test</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EnhancedAPIDocumentation;
