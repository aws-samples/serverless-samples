// Service Integration Types
export interface ServiceIntegrationOperation {
  name: string;
  template: string;
  request: string;
  context: any;
}

export interface ServiceIntegration {
  service: string;
  operations: ServiceIntegrationOperation[];
}

// Import service integration files
import sqsSendMessageTemplate from './sqs/send-message/template.vtl?raw';
import sqsSendMessageRequest from './sqs/send-message/request.http?raw';
import sqsSendMessageContext from './sqs/send-message/context.json';
import sqsReceiveMessageTemplate from './sqs/receive-message/template.vtl?raw';
import sqsReceiveMessageRequest from './sqs/receive-message/request.http?raw';
import sqsReceiveMessageContext from './sqs/receive-message/context.json';
import sqsDeleteMessageTemplate from './sqs/delete-message/template.vtl?raw';
import sqsDeleteMessageRequest from './sqs/delete-message/request.http?raw';
import sqsDeleteMessageContext from './sqs/delete-message/context.json';
import sqsPurgeQueueTemplate from './sqs/purge-queue/template.vtl?raw';
import sqsPurgeQueueRequest from './sqs/purge-queue/request.http?raw';
import sqsPurgeQueueContext from './sqs/purge-queue/context.json';
import kinesisPutRecordTemplate from './kinesis/put-record/template.vtl?raw';
import kinesisPutRecordRequest from './kinesis/put-record/request.http?raw';
import kinesisPutRecordContext from './kinesis/put-record/context.json';
import stepFunctionsStartExecutionTemplate from './stepfunctions/start-execution/template.vtl?raw';
import stepFunctionsStartExecutionRequest from './stepfunctions/start-execution/request.http?raw';
import stepFunctionsStartExecutionContext from './stepfunctions/start-execution/context.json';
import stepFunctionsStopExecutionTemplate from './stepfunctions/stop-execution/template.vtl?raw'
import stepFunctionsStopExecutionRequest from './stepfunctions/stop-execution/request.http?raw';
import stepFunctionsStopExecutionContext from './stepfunctions/stop-execution/context.json';
import stepFunctionsStartSyncExecutionTemplate from './stepfunctions/start-sync-execution/template.vtl?raw'
import stepFunctionsStartSyncExecutionRequest from './stepfunctions/start-sync-execution/request.http?raw';
import stepFunctionsStartSyncExecutionContext from './stepfunctions/start-sync-execution/context.json';
// Define service integrations
export const serviceIntegrations: ServiceIntegration[] = [
  {
    service: 'SQS',
    operations: [
      {
        name: 'send-message',
        template: sqsSendMessageTemplate,
        request: sqsSendMessageRequest,
        context: sqsSendMessageContext
      },
      {
        name: 'receive-message',
        template: sqsReceiveMessageTemplate,
        request: sqsReceiveMessageRequest,
        context: sqsReceiveMessageContext
      },
      {
        name: 'delete-message',
        template: sqsDeleteMessageTemplate,
        request: sqsDeleteMessageRequest,
        context: sqsDeleteMessageContext
      },
      {
        name: 'purge-queue',
        template: sqsPurgeQueueTemplate,
        request: sqsPurgeQueueRequest,
        context: sqsPurgeQueueContext
      }
    ]
  },
  {
    service: 'Kinesis',
    operations: [
      {
        name: 'put-record',
        template: kinesisPutRecordTemplate,
        request: kinesisPutRecordRequest,
        context: kinesisPutRecordContext
      }
    ]
  }, 
  {
    service: 'Step Functions',
    operations: [
      {
        name: 'start-execution',
        template: stepFunctionsStartExecutionTemplate,
        request: stepFunctionsStartExecutionRequest,
        context: stepFunctionsStartExecutionContext
      }, 
      {
        name: 'stop-execution',
        template: stepFunctionsStopExecutionTemplate,
        request: stepFunctionsStopExecutionRequest,
        context: stepFunctionsStopExecutionContext
      }, 
      {
        name: 'start-sync-execution',
        template: stepFunctionsStartSyncExecutionTemplate,
        request: stepFunctionsStartSyncExecutionRequest,
        context: stepFunctionsStartSyncExecutionContext
      }
    ]
  }
];

// Helper function to get all available services
export const getAvailableServices = (): string[] => {
  return serviceIntegrations.map(integration => integration.service);
};

// Helper function to get operations for a specific service
export const getOperationsForService = (service: string): ServiceIntegrationOperation[] => {
  const integration = serviceIntegrations.find(i => i.service === service);
  return integration ? integration.operations : [];
};

// Helper function to get operation names for a specific service
export const getOperationNamesForService = (service: string): string[] => {
  const operations = getOperationsForService(service);
  return operations.map(op => op.name);
};

// Helper function to get a specific operation
export const getOperation = (service: string, operationName: string): ServiceIntegrationOperation | undefined => {
  const integration = serviceIntegrations.find(i => i.service === service);
  if (!integration) return undefined;
  
  return integration.operations.find(op => op.name === operationName);
};
