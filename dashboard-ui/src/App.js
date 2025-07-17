import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // Assuming you have some basic styles
import SearchResults from './components/SearchResults'; // Make sure this path is correct

// Determine the correct API base URL based on the environment
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://project-sentinel-2.onrender.com' // Your live backend URL
  : 'http://localhost:8000'; // Your local backend URL

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false); // To track if a search has been performed

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError('');
    setResults([]);
    setSearched(true); // Mark that a search has been initiated

    try {
      // Use the environment-aware API_BASE_URL
      const response = await axios.post(`${API_BASE_URL}/v1/screen`, {
        entity_name: searchTerm,
      });
      setResults(response.data.matches || []);
    } catch (err) {
      console.error(err); // Log the full error for debugging
      setError('Search failed. Please check the connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Project Sentinel: AML/CFT Compliance Solution</h1>
        <div className="search-container">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter entity name to screen"
          />
          <button onClick={handleSearch} disabled={loading}>
            {loading ? 'Scanning...' : 'Scan'}
          </button>
        </div>

        <div className="results-container">
          {loading && <p>Loading...</p>}
          {error && <p className="error-message">{error}</p>}
          
          {!loading && !error && searched && results.length === 0 && (
            <p>No matches found for your query.</p>
          )}

          {!loading && !error && results.length > 0 && (
            <SearchResults results={results} apiBaseUrl={API_BASE_URL} />
          )}
        </div>
      </header>
    </div>
  );
}

export default App;
