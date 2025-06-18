import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  FormField,
  Box,
  Alert,
  ColumnLayout,
  Grid,
  Tabs,
  Select,
  SelectProps,
  Flashbar
} from '@cloudscape-design/components';
import { getAvailableServices, getOperationNamesForService, getOperation } from '../service-integrations';
import CodeEditor from './CodeEditor';
import JsonView from './JsonView';
import ContextVariablesHelper from './ContextVariablesHelper';

const DEFAULT_REQUEST_TEMPLATE = `#set($allParams = $input.params())
{
  "params" : {
    #foreach($type in $allParams.keySet())
    #set($params = $allParams.get($type))
    "$type" : {
      #foreach($paramName in $params.keySet())
      "$paramName" : "$util.escapeJavaScript($params.get($paramName))"
      #if($foreach.hasNext),#end
      #end
    }
    #if($foreach.hasNext),#end
    #end
  }
}`;

const DEFAULT_RESPONSE_TEMPLATE = `#set($inputRoot = $input.path('$'))
{
  "result": $input.json('$'),
  "requestId": "$context.requestId"
};`

// Generate default context variables template
const generateDefaultContextVariables = () => {
  return {
    accountId: "",
    apiId: "",
    httpMethod: "GET",
    resourcePath: "/resource",
    stage: "dev",
    requestId: "",
    identity: {
      sourceIp: "192.168.0.1",
      userAgent: "Mozilla/5.0"
    },
    authorizer: {
      principalId: ""
    }
  };
};

const DEFAULT_STAGE_VARIABLES = {
  environment: 'dev',
  region: 'us-east-1'
};

const DEFAULT_HTTP_REQUEST = `POST /resource?param1=value1&param2=value2 HTTP/1.1
Host: api.example.com
Content-Type: application/json

X-Api-Key: apikey123

{
  "message": "Hello, world!"
}`;

const DEFAULT_HTTP_RESPONSE = `HTTP/1.1 200 OK
Content-Type: application/json
X-Request-Id: req-12345-abcde

{
  "status": "success",
  "data": {
    "id": 123,
    "name": "Test Item"
  }
}`;

interface ApiGatewayHttpSimulatorProps {
  onProcessComplete?: (result: any) => void;
}

type ProcessingType = 'REQUEST_ONLY' | 'RESPONSE_ONLY';

interface ProcessConfig {
  type: ProcessingType;
  template: string;
  httpData: any;
  contextVariables: string;
  stageVariables: string;
  setIsProcessing: (value: boolean) => void;
  setError: (value: string | null) => void;
  setErrorDetails: (value: any | null) => void;
  setProcessedResult: (value: string) => void;
}


// Helper function to escape a template string for use in IaC
const escapeTemplateForIaC = (template: string): string => {
  return template
    .replace(/\\/g, '\\\\')  // Escape backslashes
    .replace(/"/g, '\\"')    // Escape double quotes
    .replace(/\n/g, '\\n')   // Replace newlines with \n
    .replace(/\r/g, '\\r')   // Replace carriage returns with \r
    .replace(/\t/g, '\\t');  // Replace tabs with \t
};

const ApiGatewayHttpSimulator: React.FC<ApiGatewayHttpSimulatorProps> = ({ onProcessComplete }) => {
  // Context and Stage Variables
  const [contextVariables, setContextVariables] = useState('{}');
  const [stageVariables, setStageVariables] = useState(JSON.stringify(DEFAULT_STAGE_VARIABLES, null, 2));
  
  // Request section
  const [httpRequest, setHttpRequest] = useState(DEFAULT_HTTP_REQUEST);
  const [requestTemplate, setRequestTemplate] = useState(DEFAULT_REQUEST_TEMPLATE);
  const [processedRequest, setProcessedRequest] = useState('');
  
  // Response section
  const [httpResponse, setHttpResponse] = useState(DEFAULT_HTTP_RESPONSE);
  const [responseTemplate, setResponseTemplate] = useState(DEFAULT_RESPONSE_TEMPLATE);
  const [processedResponse, setProcessedResponse] = useState('');
  
  // UI state
  const [isProcessingRequest, setIsProcessingRequest] = useState(false);
  const [isProcessingResponse, setIsProcessingResponse] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [responseError, setResponseError] = useState<string | null>(null);
  const [requestErrorDetails, setRequestErrorDetails] = useState<any | null>(null);
  const [responseErrorDetails, setResponseErrorDetails] = useState<any | null>(null);
  const [notifications, setNotifications] = useState<{ id: string; type: string; content: string; dismissible: boolean }[]>([]);
  
  // Tab state
  const [activeTabId, setActiveTabId] = useState('context');
  
  // Service Integration state
  const [selectedService, setSelectedService] = useState<SelectProps.Option | null>(null);
  const [selectedOperation, setSelectedOperation] = useState<SelectProps.Option | null>(null);
  const [availableServices, setAvailableServices] = useState<SelectProps.Option[]>([]);
  const [availableOperations, setAvailableOperations] = useState<SelectProps.Option[]>([]);
  
  // Initialize available services
  useEffect(() => {
    const services = getAvailableServices();
    setAvailableServices(
      services.map(service => ({ label: service, value: service }))
    );
  }, []);
  
  // Update available operations when selected service changes
  useEffect(() => {
    if (selectedService) {
      const operations = getOperationNamesForService(selectedService.value as string);
      setAvailableOperations(
        operations.map(op => ({ label: op, value: op }))
      );
      setSelectedOperation(null);
    } else {
      setAvailableOperations([]);
      setSelectedOperation(null);
    }
  }, [selectedService]);
  
  // Apply the selected service integration template, request, and context
  const applyServiceIntegration = () => {
    if (selectedService && selectedOperation) {
      const service = selectedService.value as string;
      const operation = selectedOperation.value as string;
      
      const integration = getOperation(service, operation);
      
      if (integration) {
        // Set the template
        setRequestTemplate(integration.template);
        
        // Set the request
        setHttpRequest(integration.request);
        
        // Set the context variables
        setContextVariables(JSON.stringify(integration.context, null, 2));
        
        // Switch to the request tab
        setActiveTabId('request');
      }
    }
  };

  // Helper function to parse error messages
  const parseErrorMessage = (error: string, errorDetails?: any): React.ReactNode => {
    // If we have detailed error information, use it to create a more informative message
    if (errorDetails) {
      const errorType = errorDetails.type || 'UNKNOWN_ERROR';
      const lineNumber = errorDetails.lineNumber;
      const columnNumber = errorDetails.columnNumber;
      const errorContext = errorDetails.context;
      
      return (
        <div>
          <div style={{ marginBottom: '8px' }}>
            {lineNumber && <span> at line {lineNumber}{columnNumber ? `, column ${columnNumber}` : ''}</span>}
          </div>
          
          <div style={{ marginBottom: '8px' }}>{error}</div>
          
          {errorContext && (
            <div style={{ marginBottom: '8px' }}>
              <strong>Context:</strong> {errorContext}
            </div>
          )}
          
        </div>
      );
    }
    
    // Fallback to the old parsing logic if no detailed error information is available
    if (error.includes('VTL syntax error')) {
      // Extract the specific syntax error if possible
      const syntaxMatch = error.match(/VTL syntax error: (.+)/);
      if (syntaxMatch && syntaxMatch[1]) {
        return `VTL Syntax Error: ${syntaxMatch[1]}`;
      }
    } else if (error.includes('Error in method invocation')) {
      // Extract the specific method error if possible
      const methodMatch = error.match(/Error in method invocation: (.+)/);
      if (methodMatch && methodMatch[1]) {
        return `Method Invocation Error: ${methodMatch[1]}`;
      }
    } else if (error.includes('JSON parsing error')) {
      // Extract the specific JSON error if possible
      const jsonMatch = error.match(/JSON parsing error: (.+)/);
      if (jsonMatch && jsonMatch[1]) {
        return `JSON Parsing Error: ${jsonMatch[1]}`;
      }
    } else if (error.includes('Error accessing path')) {
      // Extract the specific path error if possible
      const pathMatch = error.match(/Error accessing path '(.+?)': (.+)/);
      if (pathMatch && pathMatch[1] && pathMatch[2]) {
        return `Failed to access path '${pathMatch[1]}': ${pathMatch[2]}`;
      }
    }
    
    return error;
  };

  const processTemplate = async ({
    type,
    template,
    httpData,
    contextVariables,
    stageVariables,
    setIsProcessing,
    setError,
    setErrorDetails,
    setProcessedResult
  }: ProcessConfig) => {
    try {
      setError(null);
      setErrorDetails(null);
      setIsProcessing(true);
      
      // Parse JSON variables
      let contextVariablesObj = {};
      let stageVariablesObj = {};
      
      try {
        contextVariablesObj = JSON.parse(contextVariables || '{}');
        stageVariablesObj = JSON.parse(stageVariables || '{}');
      } catch (e) {
        throw new Error(`Invalid JSON: ${e}`);
      }
      
      // Create the configuration object
      const config = {
        [type === 'REQUEST_ONLY' ? 'httpRequest' : 'httpResponse']: httpData,
        [type === 'REQUEST_ONLY' ? 'requestTemplate' : 'responseTemplate']: template,
        contextVariables: {
          context: contextVariablesObj,
          stageVariables: stageVariablesObj
        },
        processingType: type
      };
      
      // Call the API
      const response = await fetch('/api/process-vtl', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) {
        const errorResponse = await response.json();
        if (errorResponse.errorDetails) {
          setErrorDetails(errorResponse.errorDetails);
        }
        throw new Error(errorResponse.error || `API request failed with status ${response.status}`);
      }
      
      const result = await response.text();
      setProcessedResult(result);
      return result;
      
    } catch (err: any) {
      setError(`Error processing ${type.toLowerCase().replace('_only', '')} template: ${err.message}`);
      return null;
    } finally {
      setIsProcessing(false);
    }
  };
  
  const processRequestTemplate = () => processTemplate({
    type: 'REQUEST_ONLY',
    template: requestTemplate,
    httpData: httpRequest,
    contextVariables,
    stageVariables,
    setIsProcessing: setIsProcessingRequest,
    setError: setRequestError,
    setErrorDetails: setRequestErrorDetails,
    setProcessedResult: setProcessedRequest
  });

  const processResponseTemplate = () => processTemplate({
    type: 'RESPONSE_ONLY',
    template: responseTemplate,
    httpData: httpResponse,
    contextVariables,
    stageVariables,
    setIsProcessing: setIsProcessingResponse,
    setError: setResponseError,
    setErrorDetails: setResponseErrorDetails,
    setProcessedResult: setProcessedResponse
  });

  // Function to copy template as escaped string
  const copyTemplateAsString = (template: string, type: 'request' | 'response') => {
    try {
      const escapedTemplate = escapeTemplateForIaC(template);
      navigator.clipboard.writeText(escapedTemplate);
      
      // Show notification
      const newNotification = {
        id: `copy-${Date.now()}`,
        type: 'success',
        content: `${type === 'request' ? 'Request' : 'Response'} template copied as escaped string`,
        dismissible: true
      };
      
      setNotifications([...notifications, newNotification]);
      
      // Auto-dismiss after 3 seconds
      setTimeout(() => {
        setNotifications(notifications => 
          notifications.filter(n => n.id !== newNotification.id)
        );
      }, 3000);
    } catch (error) {
      console.error('Failed to copy template:', error);
      
      // Show error notification
      const errorNotification = {
        id: `copy-error-${Date.now()}`,
        type: 'error',
        content: `Failed to copy template: ${error}`,
        dismissible: true
      };
      
      setNotifications([...notifications, errorNotification]);
    }
  };

  // Full flow processing has been removed

  return (
    <Container>
      {notifications.length > 0 && (
        <Flashbar items={notifications.map(n => ({
          id: n.id,
          type: n.type as any,
          content: n.content,
          dismissible: n.dismissible,
          onDismiss: () => {
            setNotifications(notifications.filter(item => item.id !== n.id));
          }
        }))} />
      )}
      <SpaceBetween direction="vertical" size="l">
        <Header
          variant="h1"
          description="Simulate API Gateway VTL template processing with HTTP format requests and responses"
          actions={
            <SpaceBetween direction="horizontal" size="m">
              <Header variant='h3'> Use Blueprints </Header>
              <Select
                selectedOption={selectedService}
                onChange={({ detail }) => setSelectedService(detail.selectedOption)}
                options={availableServices}
                placeholder="Select service"
                filteringType="auto"
                empty="No services available"
              />
              <Select
                selectedOption={selectedOperation}
                onChange={({ detail }) => setSelectedOperation(detail.selectedOption)}
                options={availableOperations}
                placeholder="Select operation"
                filteringType="auto"
                empty="Select a service first"
                disabled={!selectedService}
              />
              <Button
                onClick={applyServiceIntegration}
                disabled={!selectedService || !selectedOperation}
              >
                Apply
              </Button>
            </SpaceBetween>
          }
        >
          API Gateway VTL Editor
        </Header>

        <Tabs
          activeTabId={activeTabId}
          onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
          tabs={[
            {
              id: 'context',
              label: 'Context Variables',
              content: (
                <ColumnLayout columns={2} variant="text-grid">
                  <div>
                  <FormField 
                    label="Context Variables" 
                    description={
                      <SpaceBetween direction="horizontal" size="xs">
                        <ContextVariablesHelper 
                          onInsert={(variable) => {
                            try {
                              // Parse current context variables
                              const contextObj = JSON.parse(contextVariables || '{}');
                              
                              // Create nested structure based on the variable path
                              const parts = variable.replace('$context.', '').split('.');
                              let current = contextObj;
                              
                              // Build the nested structure
                              for (let i = 0; i < parts.length - 1; i++) {
                                if (!current[parts[i]]) {
                                  current[parts[i]] = {};
                                }
                                current = current[parts[i]];
                              }
                              
                              // Set the leaf value as empty string
                              current[parts[parts.length - 1]] = "";
                              
                              // Update the context variables
                              setContextVariables(JSON.stringify(contextObj, null, 2));
                            } catch (e) {
                              console.error('Error inserting context variable:', e);
                            }
                          }}
                        />
                        <Button 
                          variant="link" 
                          onClick={() => {
                            setContextVariables(JSON.stringify(generateDefaultContextVariables(), null, 2));
                          }}
                        >
                          Insert default context variables
                        </Button>
                      </SpaceBetween>
                    }
                  />
                    <CodeEditor
                      language="json"
                      value={contextVariables}
                      onChange={setContextVariables}
                      height="400px"
                    />
                  </div>
                  <div>
                  <FormField label="Stage Variables" />
                    <CodeEditor
                      language="json"
                      value={stageVariables}
                      onChange={setStageVariables}
                      height="400px"
                    />
                  </div>
                </ColumnLayout>
              )
            },
            {
              id: 'request',
              label: 'Request',
              content: (
                <SpaceBetween direction="vertical" size="l">
                  <ColumnLayout columns={2}>
                  <div>
                    <FormField label="HTTP Request" />
                      <CodeEditor
                        language="http"
                        value={httpRequest}
                        onChange={setHttpRequest}
                        height="400px"
                      />
                  </div>
                  <div>
                    <FormField 
                      label={
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                          <span>Request Mapping Template</span>
                          <Button 
                            variant="link" 
                            onClick={() => copyTemplateAsString(requestTemplate, 'request')}
                          >
                            Copy as string
                          </Button>
                        </div>
                      }
                    />
                      <CodeEditor
                        language="velocity"
                        value={requestTemplate}
                        onChange={setRequestTemplate}
                        height="400px"
                      />
                  </div>
                  </ColumnLayout>

                  <Button
                    variant="primary"
                    onClick={processRequestTemplate}
                    loading={isProcessingRequest}
                  >
                    Process Request Template
                  </Button>

                  {requestError && (
                    <Alert type="error" header="Request Processing Error">
                      {parseErrorMessage(requestError, requestErrorDetails)}
                      {!requestErrorDetails && <p><strong>Full error:</strong> {requestError}</p>}
                    </Alert>
                  )}

                  {processedRequest && (
                    <div>
                      <FormField label="Result" />
                      <JsonView src={processedRequest}/>
                    </div>
                  )}
                </SpaceBetween>
              )
            },
            {
              id: 'response',
              label: 'Response',
              content: (
                <SpaceBetween direction="vertical" size="l">
                  <ColumnLayout columns={2} variant="text-grid">
                  <div>
                    <FormField label="HTTP Response" />
                      <CodeEditor
                        language="http"
                        value={httpResponse}
                        onChange={setHttpResponse}
                        height="400px"
                      />
                    </div>

                    <div>
                    <FormField 
                      label={
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                          <span>Response Mapping Template</span>
                          <Button 
                            variant="link" 
                            onClick={() => copyTemplateAsString(responseTemplate, 'response')}
                          >
                            Copy as string
                          </Button>
                        </div>
                      }
                    />
                      <CodeEditor
                        language="velocity"
                        value={responseTemplate}
                        onChange={setResponseTemplate}
                        height="400px"
                      />
                    </div>
                  </ColumnLayout>

                  <Button
                    variant="primary"
                    onClick={processResponseTemplate}
                    loading={isProcessingResponse}
                  >
                    Process Response Template
                  </Button>

                  {responseError && (
                    <Alert type="error" header="Response Processing Error">
                      {parseErrorMessage(responseError, responseErrorDetails)}
                      {!responseErrorDetails && <p><strong>Full error:</strong> {responseError}</p>}
                    </Alert>
                  )}

                  {processedResponse && (
                    <FormField label="Result">
                      <JsonView src={processedResponse} />
                    </FormField>
                  )}
                </SpaceBetween>
              )
            }
          ]}
        />


      </SpaceBetween>
    </Container>
  );
};

export default ApiGatewayHttpSimulator;
