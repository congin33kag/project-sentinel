import React, { useState } from 'react';
import axios from 'axios';
import SearchResults from './components/SearchResults';

const containerStyle = {
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'flex-start',
  background: '#f4f8fb',
  padding: '40px 20px',
  color: '#1e2a38',
};

const titleStyle = {
  fontSize: '32px',
  fontWeight: 600,
  marginBottom: '40px',
};

const searchBarWrapper = {
  display: 'flex',
  width: '100%',
  maxWidth: '600px',
  marginBottom: '24px',
};

const inputStyle = {
  flex: 1,
  padding: '12px 16px',
  border: '1px solid #cfd8e3',
  borderRadius: '8px 0 0 8px',
  fontSize: '16px',
  outline: 'none',
};

const buttonStyle = {
  padding: '12px 24px',
  border: 'none',
  background: '#1e62d0',
  color: '#ffffff',
  fontSize: '16px',
  fontWeight: 500,
  borderRadius: '0 8px 8px 0',
  cursor: 'pointer',
};

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('http://localhost:8000/v1/screen', { entity_name: query });
      setResults(response.data.matches);
      setSearched(true);
    } catch (err) {
      setError('Search failed');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={containerStyle}>
      <h1 style={titleStyle}>Project Sentinel: AML/CFT Compliance Solution</h1>
      <div style={searchBarWrapper}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter entity or person name"
          style={inputStyle}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button onClick={handleSearch} style={buttonStyle}>Scan</button>
      </div>
      {loading && <p>Scanning...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {searched && !loading && results.length === 0 && (
        <p style={{ marginTop: '20px', color: '#51606f' }}>No matches found for your query.</p>
      )}
      {results.length > 0 && <SearchResults results={results} />}
    </div>
  );
}

export default App;
