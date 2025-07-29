import React from 'react';

function App() {
  return (
    <div style={{ 
      fontFamily: 'Arial, sans-serif', 
      maxWidth: '1200px', 
      margin: '0 auto', 
      padding: '20px' 
    }}>
      <header style={{ 
        textAlign: 'center', 
        marginBottom: '40px',
        borderBottom: '2px solid #007bff',
        paddingBottom: '20px'
      }}>
        <h1 style={{ color: '#007bff', fontSize: '2.5rem', margin: 0 }}>
          RegulensAI
        </h1>
        <p style={{ color: '#666', fontSize: '1.2rem', margin: '10px 0 0 0' }}>
          Enterprise Financial Compliance Platform
        </p>
      </header>

      <main>
        <div style={{ 
          background: '#f8f9fa', 
          padding: '30px', 
          borderRadius: '8px',
          marginBottom: '30px'
        }}>
          <h2 style={{ color: '#28a745', marginTop: 0 }}>
            ✅ Platform Successfully Deployed
          </h2>
          <p style={{ color: '#333', lineHeight: '1.6' }}>
            Your RegulensAI Financial Compliance Platform is now running and ready for configuration.
          </p>
        </div>

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
          gap: '20px',
          marginBottom: '30px'
        }}>
          <div style={{ 
            background: 'white', 
            padding: '20px', 
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <h3 style={{ color: '#007bff', marginTop: 0 }}>🔍 Core Features</h3>
            <ul style={{ color: '#333', lineHeight: '1.6' }}>
              <li>Real-time regulatory monitoring</li>
              <li>AI-powered compliance analysis</li>
              <li>AML/KYC automation</li>
              <li>Risk scoring and analytics</li>
              <li>Compliance workflow management</li>
            </ul>
          </div>

          <div style={{ 
            background: 'white', 
            padding: '20px', 
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <h3 style={{ color: '#007bff', marginTop: 0 }}>📊 Access Points</h3>
            <ul style={{ color: '#333', lineHeight: '1.6' }}>
              <li>API Documentation: <a href="/docs" target="_blank">/docs</a></li>
              <li>Health Check: <a href="/api/v1/health" target="_blank">/api/v1/health</a></li>
              <li>Monitoring: <a href="http://localhost:16686" target="_blank">Jaeger</a></li>
              <li>Analytics: <a href="http://localhost:3001" target="_blank">Grafana</a></li>
            </ul>
          </div>
        </div>

        <div style={{ 
          background: '#fff3cd', 
          border: '1px solid #ffeaa7', 
          padding: '20px', 
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: '#856404', marginTop: 0 }}>⚠️ Next Steps</h3>
          <ol style={{ color: '#856404', lineHeight: '1.6' }}>
            <li>Configure your Supabase database credentials in the .env file</li>
            <li>Add your OpenAI/Claude API keys for AI features</li>
            <li>Set up regulatory data source API keys</li>
            <li>Configure integration endpoints for your core banking systems</li>
          </ol>
        </div>

        <div style={{ 
          textAlign: 'center',
          padding: '20px',
          color: '#666',
          borderTop: '1px solid #dee2e6'
        }}>
          <p>
            <strong>RegulensAI v1.0.0</strong> | Built for enterprise financial compliance
          </p>
        </div>
      </main>
    </div>
  );
}

export default App; 