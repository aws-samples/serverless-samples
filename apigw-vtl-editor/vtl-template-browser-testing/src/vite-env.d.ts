/// <reference types="vite/client" />

declare module 'react-json-view' {
  import React from 'react';
  
  interface ReactJsonProps {
    src: object;
    name?: string | null;
    theme?: string;
    style?: React.CSSProperties;
    iconStyle?: string;
    indentWidth?: number;
    collapsed?: boolean;
    collapseStringsAfterLength?: number;
    shouldCollapse?: (field: any) => boolean;
    sortKeys?: boolean;
    quotesOnKeys?: boolean;
    displayDataTypes?: boolean;
    displayObjectSize?: boolean;
    enableClipboard?: boolean;
    onEdit?: (edit: any) => void;
    onAdd?: (add: any) => void;
    onDelete?: (delete: any) => void;
    onSelect?: (select: any) => void;
    validationMessage?: string;
  }
  
  const ReactJson: React.FC<ReactJsonProps>;
  export default ReactJson;
}
