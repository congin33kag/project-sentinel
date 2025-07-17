import React from 'react';
import axios from 'axios';
import EntityProfilePage from './EntityProfilePage';

// Determine API base URL based on environment
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://project-sentinel-2.onrender.com'
  : 'http://localhost:8000';

const cardStyle = {
  background: '#ffffff',
  borderRadius: '8px',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
  padding: '16px',
  marginBottom: '16px',
  cursor: 'pointer',
  transition: 'transform 0.1s ease-in-out',
};

const badgeStyle = {
  display: 'inline-block',
  padding: '4px 8px',
  borderRadius: '4px',
  fontSize: '12px',
  marginRight: '8px',
  background: '#e7f1ff',
  color: '#1e62d0',
};

function SearchResults({ results }) {
  const [selectedEntity, setSelectedEntity] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleResultClick = async (entityId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/v1/entity/${entityId}`);
      setSelectedEntity(response.data);
    } catch (err) {
      setError('Failed to fetch entity details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!results || results.length === 0) return null;

  return (
    <div style={{ marginTop: '32px' }}>
      <h2 style={{ color: '#1e2a38', marginBottom: '16px' }}>Results</h2>
      {results.map((result) => (
        <div
          key={result.entity_id || result.id}
          style={cardStyle}
          onClick={() => handleResultClick(result.entity_id || result.id)}
          onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-2px)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, color: '#0b1f33' }}>{result.name}</h3>
            <span style={{ ...badgeStyle }}>{result.source}</span>
          </div>
          <p style={{ margin: '8px 0 0', color: '#51606f' }}>{result.type}</p>
        </div>
      ))}
      {loading && <p>Loading details...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {selectedEntity && (
        <div style={{ marginTop: '40px' }}>
          <EntityProfilePage entity={selectedEntity} />
        </div>
      )}
    </div>
  );
}

export default SearchResults; 