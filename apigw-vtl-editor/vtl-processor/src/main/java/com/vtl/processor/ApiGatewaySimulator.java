package com.vtl.processor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.jayway.jsonpath.JsonPath;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.app.VelocityEngine;

import java.io.StringWriter;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Logger;
import java.util.logging.Level;

/**
 * Simulates the API Gateway request/response flow with VTL templates
 */
public class ApiGatewaySimulator {
    private static final Logger LOGGER = Logger.getLogger(ApiGatewaySimulator.class.getName());
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final VelocityEngine velocityEngine;
    
    /**
     * Constructor that takes a VelocityEngine instance
     * @param velocityEngine The VelocityEngine instance to use
     */
    public ApiGatewaySimulator(VelocityEngine velocityEngine) {
        this.velocityEngine = velocityEngine;
    }
    
    /**
     * Default constructor that creates a new VelocityEngine instance
     * @deprecated Use the constructor that takes a VelocityEngine instance
     */
    @Deprecated
    public ApiGatewaySimulator() {
        // Create a new VelocityEngine for backward compatibility
        this.velocityEngine = new VelocityEngine();
        this.velocityEngine.init();
    }
    
    /**
     * Processes the request mapping template
     */
    public String processRequestTemplate(
        JsonNode requestHeaders,
        JsonNode queryParams,
        JsonNode pathParams,
        String requestBody,
        String requestTemplate,
        ContextVariableProvider contextProvider
    ) throws Exception {
        try {
            // Log input parameters for debugging
            LOGGER.info("Processing request template with:");
            LOGGER.info("Headers: " + requestHeaders);
            LOGGER.info("Query params: " + queryParams);
            LOGGER.info("Path params: " + pathParams);
            LOGGER.info("Request body: " + requestBody);
            LOGGER.info("Template: " + requestTemplate);
            
            // Create maps for headers, path parameters, and query parameters
            Map<String, String> headers = new HashMap<>();
            requestHeaders.fields().forEachRemaining(entry -> {
                headers.put(entry.getKey(), entry.getValue().asText());
                LOGGER.info("Header: " + entry.getKey() + " = " + entry.getValue().asText());
            });
            
            Map<String, String> pathParameters = new HashMap<>();
            pathParams.fields().forEachRemaining(entry -> {
                pathParameters.put(entry.getKey(), entry.getValue().asText());
            });
            
            Map<String, String> queryParameters = new HashMap<>();
            queryParams.fields().forEachRemaining(entry -> {
                queryParameters.put(entry.getKey(), entry.getValue().asText());
            });
            
            // Process the template using the common method
            return processTemplate(
                requestBody,
                requestTemplate,
                contextProvider,
                headers,
                pathParameters,
                queryParameters,
                "requestTemplate",
                "request"
            );
        } catch (Exception e) {
            // Enhance error message with more context
            Map<String, Object> errorDetails = enhanceErrorMessage(e, "request");
            // Attach error details to the exception
            e.addSuppressed(new VTLErrorDetailsException(errorDetails));
            throw e;
        }
    }
    
    /**
     * Processes the response mapping template
     */
    public String processResponseTemplate(
        String backendResponse,
        String responseTemplate,
        ContextVariableProvider contextProvider
    ) throws Exception {
        try {
            // Log input parameters for debugging
            LOGGER.info("Processing response template with:");
            LOGGER.info("Backend response: " + backendResponse);
            LOGGER.info("Template: " + responseTemplate);
            
            // For response templates, we use empty maps for headers, path params, and query params
            Map<String, String> emptyMap = new HashMap<>();
            
            // Process the template using the common method
            return processTemplate(
                backendResponse,
                responseTemplate,
                contextProvider,
                emptyMap,
                emptyMap,
                emptyMap,
                "responseTemplate",
                "response"
            );
        } catch (Exception e) {
            // Enhance error message with more context
            Map<String, Object> errorDetails = enhanceErrorMessage(e, "response");
            // Attach error details to the exception
            e.addSuppressed(new VTLErrorDetailsException(errorDetails));
            throw e;
        }
    }
    
    /**
     * Common method to process both request and response templates
     */
    private String processTemplate(
        String body,
        String template,
        ContextVariableProvider contextProvider,
        Map<String, String> headers,
        Map<String, String> pathParameters,
        Map<String, String> queryParameters,
        String templateName,
        String templateType
    ) throws Exception {
        // Create Velocity context
        VelocityContext context = new VelocityContext();
        
        // Add parameters to context
        context.put("header", headers);
        context.put("path", pathParameters);
        context.put("query", queryParameters);
        
        // Create the InputWrapper with all required methods
        InputWrapper input = new InputWrapper(body, pathParameters, queryParameters, headers);
        
        // Add the input object to the Velocity context
        context.put("input", input);
                    
        // Add utility functions
        context.put("util", new VelocityUtility());
        
        // Add context variables
        context.put("context", contextProvider.getContextVariables());
        
        // Add stage variables
        context.put("stageVariables", contextProvider.getStageVariables());
        
        // Process the template
        StringWriter writer = new StringWriter();
        try {
            velocityEngine.evaluate(context, writer, templateName, template);
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error evaluating template: " + e.getMessage(), e);
            throw e;
        }
        
        String result = writer.toString();
        LOGGER.info("Template evaluation result: " + result);
        
        return result;
    }
    
    /**
     * Helper method to enhance error messages with more context
     * @return Map containing detailed error information
     */
    private Map<String, Object> enhanceErrorMessage(Exception e, String templateType) {
        String errorMessage = e.getMessage();
        String errorType = "UNKNOWN_ERROR";
        int lineNumber = -1;
        int columnNumber = -1;
        String errorContext = null;
        
        // Extract line and column information if available
        if (e instanceof org.apache.velocity.exception.ParseErrorException) {
            org.apache.velocity.exception.ParseErrorException parseError = 
                (org.apache.velocity.exception.ParseErrorException) e;
            errorType = "SYNTAX_ERROR";
            errorMessage = "VTL syntax error in " + templateType + " template: " + errorMessage;
            
            // Extract line and column information
            lineNumber = parseError.getLineNumber();
            columnNumber = parseError.getColumnNumber();
        } else if (e instanceof org.apache.velocity.exception.MethodInvocationException) {
            org.apache.velocity.exception.MethodInvocationException methodError = 
                (org.apache.velocity.exception.MethodInvocationException) e;
            
            // Check if this is a reference error or a method error
            if (e.getMessage().contains("reference is not defined") || 
                (e.getCause() != null && e.getCause().getMessage() != null && 
                 e.getCause().getMessage().contains("reference is not defined"))) {
                
                // This is likely a reference error
                errorType = "REFERENCE_ERROR";
                errorMessage = "Reference error in " + templateType + " template: " + errorMessage;
                
                // Extract variable name if possible
                if (errorMessage.contains("$")) {
                    String varName = errorMessage.substring(
                        errorMessage.indexOf("$"), 
                        errorMessage.contains(" ") ? errorMessage.indexOf(" ", errorMessage.indexOf("$")) : errorMessage.length()
                    ).trim();
                    errorContext = "Variable: " + varName;
                }
            } else {
                // This is a regular method invocation error
                errorType = "METHOD_ERROR";
                errorMessage = "Error in method invocation in " + templateType + " template: " + errorMessage;
                
                // Try to extract the reference that caused the error
                if (e.getCause() != null && e.getCause().getMessage() != null) {
                    errorMessage += " - " + e.getCause().getMessage();
                    
                    // Extract method name if possible
                    String causeMessage = e.getCause().getMessage();
                    if (causeMessage.contains("$")) {
                        String methodName = causeMessage.substring(
                            causeMessage.indexOf("$"), 
                            causeMessage.contains("(") ? causeMessage.indexOf("(") : causeMessage.length()
                        ).trim();
                        errorContext = "Method: " + methodName;
                    }
                }
            }
            
            // Get line number if available
            lineNumber = methodError.getLineNumber();
        } else if (e instanceof org.apache.velocity.exception.ResourceNotFoundException) {
            errorType = "RESOURCE_ERROR";
            errorMessage = "Resource not found in " + templateType + " template: " + errorMessage;
            
            // Extract variable name if possible
            if (errorMessage.contains("$")) {
                String varName = errorMessage.substring(
                    errorMessage.indexOf("$"), 
                    errorMessage.contains(" ") ? errorMessage.indexOf(" ", errorMessage.indexOf("$")) : errorMessage.length()
                ).trim();
                errorContext = "Variable: " + varName;
            }
        }
        
        // Replace the exception message
        try {
            java.lang.reflect.Field messageField = Throwable.class.getDeclaredField("detailMessage");
            messageField.setAccessible(true);
            messageField.set(e, errorMessage);
        } catch (Exception ex) {
            // If we can't modify the message, just log it
            LOGGER.info("Enhanced error message: " + errorMessage);
        }
        
        // Create a map with all the error details
        Map<String, Object> errorDetails = new HashMap<>();
        errorDetails.put("message", errorMessage);
        errorDetails.put("type", errorType);
        errorDetails.put("templateType", templateType);
        
        if (lineNumber >= 0) {
            errorDetails.put("lineNumber", lineNumber);
        }
        
        if (columnNumber >= 0) {
            errorDetails.put("columnNumber", columnNumber);
        }
        
        if (errorContext != null) {
            errorDetails.put("context", errorContext);
        }
        
        return errorDetails;
    }
}
