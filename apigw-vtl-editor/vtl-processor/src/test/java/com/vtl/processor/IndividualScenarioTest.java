package com.vtl.processor;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.lang.StringEscapeUtils;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInfo;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * This class provides individual test methods for each scenario.
 * Each test can be run independently, making it easier to debug and maintain.
 */
public class IndividualScenarioTest {

    private VTLProcessorHandler handler;
    private ObjectMapper objectMapper;
    private Context context;

    @BeforeEach
    void setUp() {
        handler = new VTLProcessorHandler();
        objectMapper = new ObjectMapper();
        context = new TestContext();
    }

    // ===== REQUEST SCENARIO TESTS =====

    @Test
    @DisplayName("Request - simple_request")
    void testSimpleRequest() throws IOException {
        runScenarioTest(
            "request",
            "simple_request",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("Request - complex_template")
    void testComplexTemplate() throws IOException {
        runScenarioTest(
            "request",
            "complex_template",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("Request - parse_json")
    void testParseJson() throws IOException {
        runScenarioTest(
            "request",
            "parse_json",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    // ===== RESPONSE SCENARIO TESTS =====

    @Test
    @DisplayName("Response - simple_response")
    void testSimpleResponse() throws IOException {
        runScenarioTest(
            "response",
            "simple_response",
            "response.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("Response - parse_json_response")
    void testParseJsonResponse() throws IOException {
        runScenarioTest(
            "response",
            "parse_json_response",
            "response.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    // ===== SERVICE INTEGRATION TESTS =====

    // SQS Tests
    @Test
    @DisplayName("SQS - send-message")
    void testSqsSendMessage() throws IOException {
        runServiceIntegrationTest(
            "sqs",
            "send-message",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("SQS - receive-message")
    void testSqsReceiveMessage() throws IOException {
        runServiceIntegrationTest(
            "sqs",
            "receive-message",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("SQS - delete-message")
    void testSqsDeleteMessage() throws IOException {
        runServiceIntegrationTest(
            "sqs",
            "delete-message",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("SQS - purge-queue")
    void testSqsPurgeQueue() throws IOException {
        runServiceIntegrationTest(
            "sqs",
            "purge-queue",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    // EventBridge Tests
    @Test
    @DisplayName("EventBridge - put-events")
    void testEventBridgePutEvents() throws IOException {
        runServiceIntegrationTest(
            "eventbridge",
            "put-events",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    // Kinesis Tests
    @Test
    @DisplayName("Kinesis - put-record")
    void testKinesisPutRecord() throws IOException {
        runServiceIntegrationTest(
            "kinesis",
            "put-record",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    // AppConfig Tests
    @Test
    @DisplayName("AppConfig - get-configuration")
    void testAppConfigGetConfiguration() throws IOException {
        runServiceIntegrationTest(
            "appconfig",
            "get-configuration",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    // StepFunctions Tests
    @Test
    @DisplayName("StepFunctions - start-execution")
    void testStepFunctionsStartExecution() throws IOException {
        runServiceIntegrationTest(
            "stepfunctions",
            "start-execution",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("StepFunctions - start-sync-execution")
    void testStepFunctionsStartSyncExecution() throws IOException {
        runServiceIntegrationTest(
            "stepfunctions",
            "start-sync-execution",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    @Test
    @DisplayName("StepFunctions - stop-execution")
    void testStepFunctionsStopExecution() throws IOException {
        runServiceIntegrationTest(
            "stepfunctions",
            "stop-execution",
            "request.http",
            "template.vtl",
            "context.json",
            "expected.json"
        );
    }

    /**
     * Helper method to run a scenario test.
     */
    private void runScenarioTest(
            String type,
            String scenarioName,
            String requestFileName,
            String templateFileName,
            String contextFileName,
            String expectedFileName
    ) throws IOException {
        Path scenarioPath = Paths.get("src", "test", "resources", "scenarios", type, scenarioName);
        Path requestPath = scenarioPath.resolve(requestFileName);
        Path templatePath = scenarioPath.resolve(templateFileName);
        Path contextPath = scenarioPath.resolve(contextFileName);
        Path expectedPath = scenarioPath.resolve(expectedFileName);
        
        runTest(requestPath, templatePath, contextPath, expectedPath, type);
    }

    /**
     * Helper method to run a service integration test.
     */
    private void runServiceIntegrationTest(
            String serviceName,
            String operationName,
            String requestFileName,
            String templateFileName,
            String contextFileName,
            String expectedFileName
    ) throws IOException {
        Path operationPath = Paths.get("src", "test", "resources", "scenarios", "service-integrations", 
                                      serviceName, operationName);
        Path requestPath = operationPath.resolve(requestFileName);
        Path templatePath = operationPath.resolve(templateFileName);
        Path contextPath = operationPath.resolve(contextFileName);
        Path expectedPath = operationPath.resolve(expectedFileName);
        
        runTest(requestPath, templatePath, contextPath, expectedPath, "request");
    }

    /**
     * Core method to run a test with the given paths and type.
     */
    private void runTest(Path requestPath, Path templatePath, Path contextPath, Path expectedPath, String type) throws IOException {
        // Read files
        String requestContent = Files.readString(requestPath);
        String templateContent = Files.readString(templatePath);
        String contextContent = Files.readString(contextPath);
        String expected = Files.readString(expectedPath);
        
        // Properly escape the request/response content and template content as JSON strings
        String escapedRequestContent = StringEscapeUtils.escapeJava(requestContent);
        String escapedTemplateContent = StringEscapeUtils.escapeJava(templateContent);
        
        // Create combined input JSON
        JsonNode contextNode = objectMapper.readTree(contextContent);
        
        // Check if context variables are already in the correct format
        // The correct format should have "context" and "stageVariables" fields
        boolean isCorrectFormat = contextNode.has("context") || contextNode.has("stageVariables");
        
        // If not in correct format, restructure it
        String formattedContextContent;
        if (!isCorrectFormat) {
            // Create a wrapper object with context and empty stageVariables
            formattedContextContent = "{\n" +
                "  \"context\": " + contextContent + ",\n" +
                "  \"stageVariables\": {}\n" +
                "}";
        } else {
            formattedContextContent = contextContent;
        }
        
        // Add processing type flag to match frontend behavior
        String inputJson = "{\n" +
            "  \"" + (type.equals("request") ? "httpRequest" : "httpResponse") + "\": \"" + 
            escapedRequestContent + "\",\n" +
            "  \"" + (type.equals("request") ? "requestTemplate" : "responseTemplate") + "\": \"" + 
            escapedTemplateContent + "\",\n" +
            "  \"contextVariables\": " + formattedContextContent + ",\n" +
            "  \"processingType\": \"" + (type.equals("request") ? "REQUEST_ONLY" : "RESPONSE_ONLY") + "\"\n" +
            "}";
        
        // Create request
        APIGatewayProxyRequestEvent request = new APIGatewayProxyRequestEvent();
        request.setBody(inputJson);
        
        // Process the request
        APIGatewayProxyResponseEvent response = handler.handleRequest(request, context);
        
        // Verify the response
        assertEquals(200, response.getStatusCode(), "Response status code should be 200");
        
        String output = response.getBody();
        
        // Compare the actual output with the expected output by normalizing both
        // This handles differences in string formatting (extra quotes, etc.)
        try {
            JsonNode expectedJson = objectMapper.readTree(expected);
            JsonNode actualJson = objectMapper.readTree(output);
            assertEquals(
                objectMapper.writeValueAsString(expectedJson),
                objectMapper.writeValueAsString(actualJson),
                "Output should match expected output after normalization"
            );
        } catch (Exception e) {
            // If JSON parsing fails, fall back to direct string comparison
            assertEquals(
                expected,
                output,
                "Output should match expected output"
            );
        }
    }
}
