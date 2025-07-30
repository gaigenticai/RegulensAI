import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  Save,
  Security,
  Notifications,
  Integration,
  Backup
} from '@mui/icons-material';

const Settings = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [settings, setSettings] = useState({
    general: {
      companyName: 'RegulensAI Corp',
      timezone: 'UTC',
      language: 'en',
      dateFormat: 'YYYY-MM-DD'
    },
    security: {
      sessionTimeout: 30,
      passwordExpiry: 90,
      twoFactorAuth: true,
      auditLogging: true
    },
    notifications: {
      emailAlerts: true,
      smsAlerts: false,
      pushNotifications: true,
      weeklyReports: true
    },
    integrations: {
      apiKey: 'sk-1234567890abcdef',
      webhookUrl: 'https://api.regulens.ai/webhooks',
      syncInterval: 15
    }
  });

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleSave = () => {
            // Settings saved - notification handled by UI
    // Implement save logic
  };

  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      <Card>
        <CardContent>
          <Tabs value={activeTab} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tab label="General" />
            <Tab label="Security" />
            <Tab label="Notifications" />
            <Tab label="Integrations" />
          </Tabs>

          {/* General Settings */}
          <TabPanel value={activeTab} index={0}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Company Name"
                  value={settings.general.companyName}
                  onChange={(e) => setSettings({
                    ...settings,
                    general: { ...settings.general, companyName: e.target.value }
                  })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Timezone</InputLabel>
                  <Select
                    value={settings.general.timezone}
                    label="Timezone"
                    onChange={(e) => setSettings({
                      ...settings,
                      general: { ...settings.general, timezone: e.target.value }
                    })}
                  >
                    <MenuItem value="UTC">UTC</MenuItem>
                    <MenuItem value="EST">Eastern Time</MenuItem>
                    <MenuItem value="PST">Pacific Time</MenuItem>
                    <MenuItem value="GMT">Greenwich Mean Time</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Language</InputLabel>
                  <Select
                    value={settings.general.language}
                    label="Language"
                    onChange={(e) => setSettings({
                      ...settings,
                      general: { ...settings.general, language: e.target.value }
                    })}
                  >
                    <MenuItem value="en">English</MenuItem>
                    <MenuItem value="es">Spanish</MenuItem>
                    <MenuItem value="fr">French</MenuItem>
                    <MenuItem value="de">German</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Date Format</InputLabel>
                  <Select
                    value={settings.general.dateFormat}
                    label="Date Format"
                    onChange={(e) => setSettings({
                      ...settings,
                      general: { ...settings.general, dateFormat: e.target.value }
                    })}
                  >
                    <MenuItem value="YYYY-MM-DD">YYYY-MM-DD</MenuItem>
                    <MenuItem value="MM/DD/YYYY">MM/DD/YYYY</MenuItem>
                    <MenuItem value="DD/MM/YYYY">DD/MM/YYYY</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Security Settings */}
          <TabPanel value={activeTab} index={1}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Session Timeout (minutes)"
                  type="number"
                  value={settings.security.sessionTimeout}
                  onChange={(e) => setSettings({
                    ...settings,
                    security: { ...settings.security, sessionTimeout: parseInt(e.target.value) }
                  })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Password Expiry (days)"
                  type="number"
                  value={settings.security.passwordExpiry}
                  onChange={(e) => setSettings({
                    ...settings,
                    security: { ...settings.security, passwordExpiry: parseInt(e.target.value) }
                  })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.security.twoFactorAuth}
                      onChange={(e) => setSettings({
                        ...settings,
                        security: { ...settings.security, twoFactorAuth: e.target.checked }
                      })}
                    />
                  }
                  label="Enable Two-Factor Authentication"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.security.auditLogging}
                      onChange={(e) => setSettings({
                        ...settings,
                        security: { ...settings.security, auditLogging: e.target.checked }
                      })}
                    />
                  }
                  label="Enable Audit Logging"
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Notification Settings */}
          <TabPanel value={activeTab} index={2}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Alert Preferences
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications.emailAlerts}
                      onChange={(e) => setSettings({
                        ...settings,
                        notifications: { ...settings.notifications, emailAlerts: e.target.checked }
                      })}
                    />
                  }
                  label="Email Alerts"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications.smsAlerts}
                      onChange={(e) => setSettings({
                        ...settings,
                        notifications: { ...settings.notifications, smsAlerts: e.target.checked }
                      })}
                    />
                  }
                  label="SMS Alerts"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications.pushNotifications}
                      onChange={(e) => setSettings({
                        ...settings,
                        notifications: { ...settings.notifications, pushNotifications: e.target.checked }
                      })}
                    />
                  }
                  label="Push Notifications"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications.weeklyReports}
                      onChange={(e) => setSettings({
                        ...settings,
                        notifications: { ...settings.notifications, weeklyReports: e.target.checked }
                      })}
                    />
                  }
                  label="Weekly Reports"
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Integration Settings */}
          <TabPanel value={activeTab} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Configure external integrations and API settings
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="API Key"
                  value={settings.integrations.apiKey}
                  onChange={(e) => setSettings({
                    ...settings,
                    integrations: { ...settings.integrations, apiKey: e.target.value }
                  })}
                  fullWidth
                  type="password"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Webhook URL"
                  value={settings.integrations.webhookUrl}
                  onChange={(e) => setSettings({
                    ...settings,
                    integrations: { ...settings.integrations, webhookUrl: e.target.value }
                  })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Sync Interval (minutes)"
                  type="number"
                  value={settings.integrations.syncInterval}
                  onChange={(e) => setSettings({
                    ...settings,
                    integrations: { ...settings.integrations, syncInterval: parseInt(e.target.value) }
                  })}
                  fullWidth
                />
              </Grid>
            </Grid>
          </TabPanel>

          <Divider sx={{ my: 3 }} />

          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              startIcon={<Save />}
              onClick={handleSave}
            >
              Save Settings
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Settings;
