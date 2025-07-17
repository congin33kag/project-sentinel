import React from 'react';

function EntityProfilePage({ entity }) {
  if (!entity) {
    return <div>Loading...</div>;
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px' }}>{entity.name}</h1>
      
      <div style={{ background: '#f8f9fa', padding: '20px', marginBottom: '20px', borderRadius: '8px' }}>
        <h2>Summary</h2>
        <p><strong>Category:</strong> {entity.category}</p>
        <p><strong>Source:</strong> {entity.source}</p>
      </div>
      
      <div style={{ background: '#f8f9fa', padding: '20px', marginBottom: '20px', borderRadius: '8px' }}>
        <h2>Known Aliases</h2>
        {entity.aliases && entity.aliases.length > 0 ? (
          <ul>
            {entity.aliases.map((alias, index) => (
              <li key={index}>{alias}</li>
            ))}
          </ul>
        ) : (
          <p>No known aliases.</p>
        )}
      </div>
      
      <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px' }}>
        <h2>Sanctions Details</h2>
        {entity.sanctions && entity.sanctions.length > 0 ? (
          <ul>
            {entity.sanctions.map((sanction, index) => (
              <li key={index}>{sanction.program} - {sanction.sanctioning_body}</li>
            ))}
          </ul>
        ) : (
          <p>No sanctions details available.</p>
        )}
      </div>
    </div>
  );
}

export default EntityProfilePage; 