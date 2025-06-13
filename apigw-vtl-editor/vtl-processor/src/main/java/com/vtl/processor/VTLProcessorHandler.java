package com.vtl.processor;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyRequestEvent;
import com.amazonaws.services.lambda.runtime.events.APIGatewayProxyResponseEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.app.VelocityEngine;
import org.apache.velocity.runtime.RuntimeConstants;
import org.apache.velocity.runtime.resource.loader.StringResourceLoader;
import org.apache.velocity.runtime.resource.util.StringResourceRepository;

import java.io.StringWriter;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Logger;
import java.util.logging.Level;

public class VTLProcessorHandler implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {
    private static final Logger LOGGER = Logger.getLogger(VTLProcessorHandler.class.getName());
    
    private final ObjectMapper objectMapper;
    private final VelocityEngine velocityEngine;
    private final ApiGatewaySimulator apiGatewaySimulator;
    private final HttpFormatParser httpRequestParser;

    public VTLProcessorHandler() {
        LOGGER.info("Initializing VTLProcessorHandler");
        
        // Initialize ObjectMapper
        objectMapper = new ObjectMapper();
        
        // Initialize Velocity Engine with enhanced logging
        velocityEngine = new VelocityEngine();
        velocityEngine.setProperty(RuntimeConstants.RESOURCE_LOADER, "string");
        velocityEngine.addProperty("string.resource.loader.class", StringResourceLoader.class.getName());
        velocityEngine.addProperty("string.resource.loader.repository.static", "false");
        
        // Configure Velocity logging
        velocityEngine.setProperty("runtime.log.logsystem.class", "org.apache.velocity.runtime.log.SimpleLog4JLogSystem");
        velocityEngine.setProperty("runtime.log.logsystem.log4j.category", "velocity");
        velocityEngine.setProperty("runtime.log.logsystem.log4j.level", "DEBUG");
        
        // Enable strict reference checking to catch undefined variables
        velocityEngine.setProperty("runtime.references.strict", true);
        
        velocityEngine.init();
        
        // Initialize API Gateway Simulator with the configured VelocityEngine
        apiGatewaySimulator = new ApiGatewaySimulator(velocityEngine);
        
        // Initialize HTTP parsers
        httpRequestParser = new HttpFormatParser();
        
        LOGGER.info("VTLProcessorHandler initialization complete");
    }

    @Override
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent input, Context context) {
        LOGGER.info("Handling request: " + input.getPath());
        
        APIGatewayProxyResponseEvent response = new APIGatewayProxyResponseEvent();
        response.setHeaders(getCorsHeaders());

        try {
            // Parse the request body
            LOGGER.info("Parsing request body");
            String requestBodyString = input.getBody();
            LOGGER.info("Request body: " + requestBodyString);
            
            JsonNode requestBody = objectMapper.readTree(requestBodyString);
            
            // Check for processing type flag
            String processingType = "UNKNOWN";
            if (requestBody.has("processingType")) {
                processingType = requestBody.get("processingType").asText();
                LOGGER.info("Processing type: " + processingType);
            }
            
            // Process based on the processing type flag
            if ("REQUEST_ONLY".equals(processingType)) {
                LOGGER.info("Processing request only based on flag");
                return processRequestOnly(requestBody, response);
            } else if ("RESPONSE_ONLY".equals(processingType)) {
                LOGGER.info("Processing response only based on flag");
                return processResponseOnly(requestBody, response);
            } else {
                LOGGER.info("Unknown request type");
                response.setStatusCode(400);
                response.setBody("{\"success\":false, \"error\":\"Unknown request type\"}");
                return response;
            }
        } catch (Exception e) {
            // Handle errors
            LOGGER.log(Level.SEVERE, "Error processing request", e);
            
            ObjectNode errorResponse = objectMapper.createObjectNode();
            errorResponse.put("success", false);
            errorResponse.put("error", e.getMessage());
            
            // Check if there's detailed error information available
            VTLErrorDetailsException errorDetailsException = findErrorDetailsException(e);
            if (errorDetailsException != null) {
                Map<String, Object> errorDetails = errorDetailsException.getErrorDetails();
                
                // Add error details to the response
                ObjectNode detailsNode = objectMapper.createObjectNode();
                for (Map.Entry<String, Object> entry : errorDetails.entrySet()) {
                    if (entry.getValue() instanceof String) {
                        detailsNode.put(entry.getKey(), (String) entry.getValue());
                    } else if (entry.getValue() instanceof Number) {
                        if (entry.getValue() instanceof Integer) {
                            detailsNode.put(entry.getKey(), (Integer) entry.getValue());
                        } else if (entry.getValue() instanceof Long) {
                            detailsNode.put(entry.getKey(), (Long) entry.getValue());
                        } else if (entry.getValue() instanceof Double) {
                            detailsNode.put(entry.getKey(), (Double) entry.getValue());
                        }
                    } else if (entry.getValue() instanceof Boolean) {
                        detailsNode.put(entry.getKey(), (Boolean) entry.getValue());
                    }
                }
                errorResponse.set("errorDetails", detailsNode);
            }
            
            // Add stack trace for debugging
            errorResponse.put("stackTrace", getStackTraceAsString(e));

            response.setStatusCode(400);
            try {
                response.setBody(objectMapper.writeValueAsString(errorResponse));
            } catch (JsonProcessingException ex) {
                LOGGER.log(Level.SEVERE, "Error creating error response", ex);
                response.setBody("{\"success\":false,\"error\":\"Error processing response\"}");
            }
            
            return response;
        }
    }
    
    private APIGatewayProxyResponseEvent processRequestOnly(JsonNode requestBody, APIGatewayProxyResponseEvent response) throws Exception {
        LOGGER.info("Processing HTTP request template");
        
        // Process HTTP request template
        String httpRequest;
        if (requestBody.has("httpRequest")) {
            httpRequest = requestBody.get("httpRequest").asText();
        } else {
            throw new Exception("Missing required request parameters");
        }
        
        String template = requestBody.get("requestTemplate").asText();
        
        // Parse HTTP request
        LOGGER.info("Parsing HTTP request");   
        JsonNode parsedHttp = httpRequestParser.parseHttpRequest(httpRequest);
        
        // Process the template
        return processTemplate(
            requestBody,
            response,
            template,
            parsedHttp,
            true, // isRequest
            "HTTP Request",
            "Request Template"
        );
    }
    
    private APIGatewayProxyResponseEvent processResponseOnly(JsonNode requestBody, APIGatewayProxyResponseEvent response) throws Exception {
        LOGGER.info("Processing HTTP response template");
        
        // Process HTTP response template
        String httpResponse;
        if (requestBody.has("httpResponse")) {
            httpResponse = requestBody.get("httpResponse").asText();
        } else {
            throw new Exception("Missing required response parameters");
        }
        
        String template = requestBody.get("responseTemplate").asText();
        
        // Parse HTTP response
        LOGGER.info("Parsing HTTP response");
        JsonNode parsedHttp = httpRequestParser.parseHttpRequest(httpResponse);
        
        // Process the template
        return processTemplate(
            requestBody,
            response,
            template,
            parsedHttp,
            false, // isRequest
            "HTTP Response",
            "Response Template"
        );
    }
    
    /**
     * Common method to process both request and response templates
     */
    private APIGatewayProxyResponseEvent processTemplate(
            JsonNode requestBody, 
            APIGatewayProxyResponseEvent response,
            String template,
            JsonNode parsedHttp,
            boolean isRequest,
            String httpLogLabel,
            String templateLogLabel) throws Exception {
        
        // Get context configuration
        JsonNode contextConfig = requestBody.has("contextVariables") ? 
            requestBody.get("contextVariables") : null;
        
        // Log information
        String httpContent = isRequest ? 
            requestBody.get("httpRequest").asText() : 
            requestBody.get("httpResponse").asText();
            
        LOGGER.info(httpLogLabel + ": " + httpContent);
        LOGGER.info(templateLogLabel + ": " + template);
        LOGGER.info("Context Config: " + (contextConfig != null ? contextConfig.toString() : "null"));
        LOGGER.info("Parsed " + (isRequest ? "Request" : "Response") + ": " + parsedHttp.toString());
        
        // Create context variable provider
        LOGGER.info("Creating context variable provider");
        ContextVariableProvider contextProvider = new ContextVariableProvider(contextConfig);
        LOGGER.info("Context Variables: " + objectMapper.writeValueAsString(contextProvider.getContextVariables()));
        LOGGER.info("Stage Variables: " + objectMapper.writeValueAsString(contextProvider.getStageVariables()));
        
        // Update context with HTTP method and path if available for requests
        if (isRequest && contextProvider.getContextVariables() instanceof Map && 
            parsedHttp.has("method") && parsedHttp.has("path")) {
            
            LOGGER.info("Updating context with HTTP method and path");
            @SuppressWarnings("unchecked")
            Map<String, Object> contextMap = (Map<String, Object>) contextProvider.getContextVariables();
            contextMap.put("httpMethod", parsedHttp.get("method").asText());
            contextMap.put("resourcePath", parsedHttp.get("path").asText());
            LOGGER.info("Updated Context Variables: " + objectMapper.writeValueAsString(contextMap));
        }
        
        // Process template
        LOGGER.info("Processing " + (isRequest ? "request" : "response") + " template");
        String processedContent;
        
        if (isRequest) {
            processedContent = apiGatewaySimulator.processRequestTemplate(
                parsedHttp.get("headers"),
                parsedHttp.get("queryParams"),
                parsedHttp.get("pathParams"),
                parsedHttp.get("body").asText(),
                template,
                contextProvider
            );
        } else {
            processedContent = apiGatewaySimulator.processResponseTemplate(
                parsedHttp.get("body").asText(),
                template,
                contextProvider
            );
        }
        
        LOGGER.info("Processed " + (isRequest ? "Request" : "Response") + ": " + processedContent);
        
        response.setStatusCode(200);
        response.setBody(processedContent);
        LOGGER.info("HTTP " + (isRequest ? "request" : "response") + " template processing complete");
        
        return response;
    }
    
    
    private String getStackTraceAsString(Exception e) {
        StringBuilder sb = new StringBuilder();
        sb.append(e.getMessage()).append("\n");
        
        for (StackTraceElement element : e.getStackTrace()) {
            sb.append("    at ").append(element.toString()).append("\n");
        }
        
        return sb.toString();
    }
    
    private Map<String, String> getCorsHeaders() {
        Map<String, String> headers = new HashMap<>();
        headers.put("Access-Control-Allow-Origin", "*");
        headers.put("Access-Control-Allow-Headers", "Content-Type,X-Amz-Date,Authorization,X-Api-Key");
        headers.put("Access-Control-Allow-Methods", "OPTIONS,POST");
        return headers;
    }
    
    /**
     * Helper method to find VTLErrorDetailsException in the exception chain
     * @param e The exception to search
     * @return The VTLErrorDetailsException if found, null otherwise
     */
    private VTLErrorDetailsException findErrorDetailsException(Throwable e) {
        // Check if this exception is a VTLErrorDetailsException
        if (e instanceof VTLErrorDetailsException) {
            return (VTLErrorDetailsException) e;
        }
        
        // Check suppressed exceptions
        for (Throwable suppressed : e.getSuppressed()) {
            if (suppressed instanceof VTLErrorDetailsException) {
                return (VTLErrorDetailsException) suppressed;
            }
        }
        
        // Check cause chain
        if (e.getCause() != null && e.getCause() != e) {
            return findErrorDetailsException(e.getCause());
        }
        
        return null;
    }
}
