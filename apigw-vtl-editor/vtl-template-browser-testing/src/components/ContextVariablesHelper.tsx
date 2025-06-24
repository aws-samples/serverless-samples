import React, { useState } from 'react';
import {
  Button,
  Modal,
  Box,
  SpaceBetween,
  Header,
  Link,
  Table,
  TextFilter,
  Pagination
} from '@cloudscape-design/components';

interface ContextVariablesHelperProps {
  onInsert: (variable: string) => void;
}

// List of supported context variables from API Gateway documentation
const CONTEXT_VARIABLES = [
  { name: '$context.accountId', description: 'The AWS account ID associated with the request.' },
  { name: '$context.apiId', description: 'The identifier API Gateway assigns to your API.' },
  { name: '$context.authorizer.claims.property', description: 'A property of the claims returned from the Amazon Cognito user pool after the method caller is successfully authenticated.' },
  { name: '$context.authorizer.principalId', description: 'The principal user identification associated with the token sent by the client.' },
  { name: '$context.authorizer.property', description: 'The value of the specified key-value pair of the context map returned from an API Gateway Lambda authorizer.' },
  { name: '$context.awsEndpointRequestId', description: 'The AWS endpoint\'s request ID.' },
  { name: '$context.deploymentId', description: 'The identifier API Gateway assigns to a deployment.' },
  { name: '$context.domainName', description: 'The full domain name used to invoke the API.' },
  { name: '$context.domainPrefix', description: 'The first label of the $context.domainName.' },
  { name: '$context.error.message', description: 'The error message from API Gateway.' },
  { name: '$context.error.messageString', description: 'The quoted value of $context.error.message.' },
  { name: '$context.error.responseType', description: 'The error response type.' },
  { name: '$context.error.validationErrorString', description: 'A string containing detailed validation error messages.' },
  { name: '$context.extendedRequestId', description: 'Extended ID that API Gateway assigns to the API request.' },
  { name: '$context.httpMethod', description: 'The HTTP method used. Valid values include: DELETE, GET, HEAD, OPTIONS, PATCH, POST, and PUT.' },
  { name: '$context.identity.accountId', description: 'The AWS account ID associated with the request.' },
  { name: '$context.identity.apiKey', description: 'The API owner key associated with key-enabled API requests.' },
  { name: '$context.identity.apiKeyId', description: 'The API key ID associated with key-enabled API requests.' },
  { name: '$context.identity.caller', description: 'The principal identifier of the caller that signed the request.' },
  { name: '$context.identity.cognitoAuthenticationProvider', description: 'A comma-separated list of the Amazon Cognito authentication providers used by the caller.' },
  { name: '$context.identity.cognitoAuthenticationType', description: 'The Amazon Cognito authentication type of the caller.' },
  { name: '$context.identity.cognitoIdentityId', description: 'The Amazon Cognito identity ID of the caller.' },
  { name: '$context.identity.cognitoIdentityPoolId', description: 'The Amazon Cognito identity pool ID associated with the caller.' },
  { name: '$context.identity.principalOrgId', description: 'The AWS organization ID.' },
  { name: '$context.identity.sourceIp', description: 'The source IP address of the immediate TCP connection making the request.' },
  { name: '$context.identity.clientCert.clientCertPem', description: 'The PEM-encoded client certificate that the client presented during mutual TLS authentication.' },
  { name: '$context.identity.clientCert.subjectDN', description: 'The distinguished name of the subject of the certificate that the client presented.' },
  { name: '$context.identity.clientCert.issuerDN', description: 'The distinguished name of the issuer of the certificate that the client presented.' },
  { name: '$context.identity.clientCert.serialNumber', description: 'The serial number of the certificate.' },
  { name: '$context.identity.clientCert.validity.notBefore', description: 'The date before which the certificate is not valid.' },
  { name: '$context.identity.clientCert.validity.notAfter', description: 'The date after which the certificate is not valid.' },
  { name: '$context.identity.vpcId', description: 'The VPC ID associated with the request.' },
  { name: '$context.identity.vpceId', description: 'The VPC endpoint ID associated with the request.' },
  { name: '$context.identity.user', description: 'The principal identifier of the user that will be authorized against resource access.' },
  { name: '$context.identity.userAgent', description: 'The User-Agent header of the API caller.' },
  { name: '$context.identity.userArn', description: 'The Amazon Resource Name (ARN) of the effective user identified after authentication.' },
  { name: '$context.isCanaryRequest', description: 'Whether a request is a canary request as part of a canary release deployment.' },
  { name: '$context.path', description: 'The request path.' },
  { name: '$context.protocol', description: 'The request protocol, for example, HTTP/1.1.' },
  { name: '$context.requestId', description: 'The ID that API Gateway assigns to the API request.' },
  { name: '$context.requestOverride.header.header_name', description: 'The request header override.' },
  { name: '$context.requestOverride.path.path_name', description: 'The request path override.' },
  { name: '$context.requestOverride.querystring.querystring_name', description: 'The request query string override.' },
  { name: '$context.responseOverride.header.header_name', description: 'The response header override.' },
  { name: '$context.responseOverride.status', description: 'The response status code override.' },
  { name: '$context.requestTime', description: 'The CLF-formatted request time (dd/MMM/yyyy:HH:mm:ss +-hhmm).' },
  { name: '$context.requestTimeEpoch', description: 'The Epoch-formatted request time.' },
  { name: '$context.resourceId', description: 'The identifier that API Gateway assigns to your resource.' },
  { name: '$context.resourcePath', description: 'The path to your resource.' },
  { name: '$context.stage', description: 'The deployment stage of the API request.' },
  { name: '$context.wafResponseCode', description: 'The response received from AWS WAF.' },
  { name: '$context.webaclArn', description: 'The ARN of the web ACL that is used to monitor the request.' }
];

const ContextVariablesHelper: React.FC<ContextVariablesHelperProps> = ({ onInsert }) => {
  const [visible, setVisible] = useState(false);
  const [filterText, setFilterText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Filter variables based on search text
  const filteredVariables = CONTEXT_VARIABLES.filter(variable => 
    variable.name.toLowerCase().includes(filterText.toLowerCase()) || 
    variable.description.toLowerCase().includes(filterText.toLowerCase())
  );

  // Calculate pagination
  const totalPages = Math.ceil(filteredVariables.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const visibleVariables = filteredVariables.slice(startIndex, startIndex + itemsPerPage);

  const handleInsert = (variable: string) => {
    onInsert(variable);
    setVisible(false);
  };

  return (
    <>
      <Button variant="link" onClick={() => setVisible(true)}>
        View available context variables
      </Button>

      <Modal
        visible={visible}
        onDismiss={() => setVisible(false)}
        size="large"
        header={<Header>API Gateway Context Variables</Header>}
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setVisible(false)}>
                Close
              </Button>
            </SpaceBetween>
          </Box>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          <Box>
            <p>
              These are the context variables supported by API Gateway. Click on a variable to insert it into your context variables JSON.
              For more information, see the{' '}
              <Link external href="https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping-template-reference.html#context-variable-reference">
                API Gateway documentation
              </Link>.
            </p>
          </Box>

          <TextFilter
            filteringText={filterText}
            filteringPlaceholder="Find context variables"
            filteringAriaLabel="Filter context variables"
            onChange={({ detail }) => {
              setFilterText(detail.filteringText);
              setCurrentPage(1);
            }}
          />

          <Table
            columnDefinitions={[
              {
                id: 'variable',
                header: 'Variable',
                cell: item => (
                  <Link onFollow={() => handleInsert(item.name)}>
                    {item.name}
                  </Link>
                ),
                sortingField: 'name'
              },
              {
                id: 'description',
                header: 'Description',
                cell: item => item.description
              }
            ]}
            items={visibleVariables}
            loadingText="Loading context variables"
            trackBy="name"
            empty={
              <Box textAlign="center" color="inherit">
                <b>No context variables found</b>
                <Box padding={{ bottom: 's' }} variant="p" color="inherit">
                  No context variables match the filter criteria.
                </Box>
              </Box>
            }
            header={
              <Header
                counter={`(${filteredVariables.length})`}
              >
                Context Variables
              </Header>
            }
          />

          {totalPages > 1 && (
            <Pagination
              currentPageIndex={currentPage}
              pagesCount={totalPages}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
          )}
        </SpaceBetween>
      </Modal>
    </>
  );
};

export default ContextVariablesHelper;
