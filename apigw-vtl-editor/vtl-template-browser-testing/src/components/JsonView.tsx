import React from 'react';
import CodeEditor from './CodeEditor';

interface JsonViewProps {
  src: string;
}

const JsonView: React.FC<JsonViewProps> = ({ src }) => {
  // Try to parse and format the JSON if it's a string
  let formattedJson = '';
  
  try {
    if (typeof src === 'string') {
      // If it's an empty string, just use an empty string
      if (!src.trim()) {
        formattedJson = '';
      } else {
        // Try to parse it as JSON
        try {
          const parsed = JSON.parse(src);
          formattedJson = JSON.stringify(parsed, null, 2);
        } catch (e) {
          // If it's not valid JSON, use the original string
          formattedJson = src;
        }
      }
    } else if (src === null || src === undefined) {
      formattedJson = '';
    } else {
      // If it's already an object, stringify it
      formattedJson = JSON.stringify(src, null, 2);
    }
  } catch (e) {
    console.error('Error formatting JSON:', e);
    formattedJson = String(src);
  }

  return (
    <div style={{ border: '1px solid #eaeded', borderRadius: '4px' }}>
      {formattedJson ? (
        <CodeEditor
          language="json"
          height='400px'
          value={formattedJson}
          onChange={() => {}}
          readOnly={true}
        />
      ) : (
        <div style={{ 
          padding: '10px', 
          color: '#5f6b7a', 
          fontStyle: 'italic',
          backgroundColor: '#f8f8f8',
          height: 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          No data available
        </div>
      )}
    </div>
  );
};

export default JsonView;
