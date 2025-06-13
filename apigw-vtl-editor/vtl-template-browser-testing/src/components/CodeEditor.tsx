import React from 'react';
import Editor, { Monaco } from '@monaco-editor/react';

interface CodeEditorProps {
  language: string;
  value: string;
  onChange: (value: string) => void;
  height?: string;
  readOnly?: boolean;
}

// Register custom languages
const registerVelocityLanguage = (monaco: Monaco) => {
  // Register Velocity language if it doesn't exist
  if (!monaco.languages.getLanguages().some((lang: { id: string; }) => lang.id === 'velocity')) {
    monaco.languages.register({ id: 'velocity' });
    
    // Define syntax highlighting for Velocity
    monaco.languages.setMonarchTokensProvider('velocity', {
      tokenizer: {
        root: [
          // Comments
          [/##.*$/, 'comment'],
          [/#\*/, 'comment', '@comment'],
          
          // Directives
          [/#(if|else|elseif|end|foreach|set|include|parse|stop|break|evaluate|define|macro)/, 'keyword'],
          
          // Variables
          [/\$!?\{[^}]*\}/, 'variable'],
          [/\$!?[a-zA-Z][a-zA-Z0-9_]*/, 'variable'],
          
          // String literals
          [/"([^"\\]|\\.)*$/, 'string.invalid'],
          [/'([^'\\]|\\.)*$/, 'string.invalid'],
          [/"/, 'string', '@string_double'],
          [/'/, 'string', '@string_single'],
          
          // Numbers
          [/\d+/, 'number'],
        ],
        comment: [
          [/\*#/, 'comment', '@pop'],
          [/./, 'comment']
        ],
        string_double: [
          [/[^\\"]+/, 'string'],
          [/\\./, 'string.escape'],
          [/"/, 'string', '@pop']
        ],
        string_single: [
          [/[^\\']+/, 'string'],
          [/\\./, 'string.escape'],
          [/'/, 'string', '@pop']
        ]
      }
    });
  }
};

// Register HTTP language
const registerHttpLanguage = (monaco: Monaco) => {
  // Register HTTP language if it doesn't exist
  if (!monaco.languages.getLanguages().some((lang: { id: string; }) => lang.id === 'http')) {
    monaco.languages.register({ id: 'http' });
    
    // Define syntax highlighting for HTTP
    monaco.languages.setMonarchTokensProvider('http', {
      tokenizer: {
        root: [
          // Request line or status line
          [/^(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)(\s+)([^\s]+)(\s+)(HTTP\/\d\.\d)$/, 
            ['keyword', 'white', 'string', 'white', 'keyword']],
          [/^(HTTP\/\d\.\d)(\s+)(\d{3})(\s+)(.*)$/, 
            ['keyword', 'white', 'number', 'white', 'string']],
          
          // Headers
          [/^([A-Za-z0-9\-]+)(:)(\s+)(.*)$/, ['type', 'delimiter', 'white', 'string']],
          
          // Empty line separating headers from body
          [/^$/, 'white'],
          
          // JSON in body
          [/{/, { token: 'delimiter.curly', next: '@json_object' }],
          [/\[/, { token: 'delimiter.square', next: '@json_array' }],
        ],
        
        // JSON highlighting
        json_object: [
          [/[}\]]/, { token: 'delimiter.curly', next: '@pop' }],
          [/"([^"]*)":\s*/, 'attribute.name'],
          [/(".*?")(\s*)(:)/, ['string', 'white', 'delimiter']],
          [/,/, 'delimiter'],
          [/{/, { token: 'delimiter.curly', next: '@json_object' }],
          [/\[/, { token: 'delimiter.square', next: '@json_array' }],
          [/\d+\.\d*([eE][\-+]?\d+)?/, 'number.float'],
          [/\d+/, 'number'],
          [/true|false/, 'keyword'],
          [/null/, 'keyword'],
          [/".*?"/, 'string'],
        ],
        
        json_array: [
          [/[}\]]/, { token: '@rematch', next: '@pop' }],
          [/\[/, { token: 'delimiter.square', next: '@json_array' }],
          [/{/, { token: 'delimiter.curly', next: '@json_object' }],
          [/,/, 'delimiter'],
          [/\d+\.\d*([eE][\-+]?\d+)?/, 'number.float'],
          [/\d+/, 'number'],
          [/true|false/, 'keyword'],
          [/".*?"/, 'string'],
        ]
      }
    });
  }
};

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  language, 
  value, 
  onChange, 
  height = '200px',
  readOnly = false
}) => {
  // Map language names to Monaco editor languages
  const getMonacoLanguage = (lang: string) => {
    const languageMap: Record<string, string> = {
      'velocity': 'velocity', // Use our custom velocity language
      'http': 'http',         // Use our custom http language
      'text': 'plaintext'
    };
    
    return languageMap[lang] || lang;
  };

  // Handle editor mount to register custom languages
  const handleEditorDidMount = (editor: any, monaco: Monaco) => {
    registerVelocityLanguage(monaco);
    registerHttpLanguage(monaco);
    
    // Set editor options
    editor.updateOptions({
      fontSize: 14,
      lineHeight: 20,
      tabSize: 2,
      scrollBeyondLastLine: false,
      minimap: { enabled: false },
      wordWrap: 'on',
      wrappingIndent: 'indent',
      automaticLayout: true,
      readOnly: readOnly,
      lineNumbers: 'on',
    });
  };

  return (
    <div style={{ width: '100%', height: height }}>
      <Editor
        height={height}
        width="100%"
        language={getMonacoLanguage(language)}
        value={value}
        onChange={(value) => onChange(value || '')}
        options={{
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          wrappingIndent: 'indent',
          automaticLayout: true,
          readOnly: readOnly,
          fontSize: 14,
          lineNumbers: 'on',
          tabSize: 2
        }}
        onMount={handleEditorDidMount}
        theme="vs-light"
      />
    </div>
  );
};

export default CodeEditor;
