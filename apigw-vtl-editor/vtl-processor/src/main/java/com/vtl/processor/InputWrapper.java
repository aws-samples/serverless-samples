package com.vtl.processor;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.jayway.jsonpath.JsonPath;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;
import java.util.logging.Level;

/**
 * Wrapper class for the $input variable in API Gateway templates
 * Implements all the required methods that can be called from Velocity templates
 */
public class InputWrapper {
    private static final Logger LOGGER = Logger.getLogger(InputWrapper.class.getName());
    private final String body;
    private final Map<String, String> pathParams;
    private final Map<String, String> queryParams;
    private final Map<String, String> headers;
    private final ObjectMapper objectMapper;
    private Object parsedBody;

    public InputWrapper(String requestBody, Map<String, String> pathParams, 
                       Map<String, String> queryParams, Map<String, String> headers) {
        this.body = requestBody;
        this.pathParams = pathParams;
        this.queryParams = queryParams;
        this.headers = headers;
        this.objectMapper = new ObjectMapper();
        
        // Try to parse the request body as JSON and convert to Map/List
        try {
            JsonNode jsonNode = objectMapper.readTree(requestBody);
            
            // Convert JsonNode to Map or List based on the node type
            if (jsonNode.isObject()) {
                this.parsedBody = objectMapper.convertValue(jsonNode, Map.class);
            } else if (jsonNode.isArray()) {
                this.parsedBody = objectMapper.convertValue(jsonNode, List.class);
            } else {
                // This should not happen based on our assumption
                LOGGER.warning("JSON is neither an object nor an array");
                this.parsedBody = null;
            }
        } catch (Exception e) {
            // If parsing fails, leave parsedBody as null
            LOGGER.warning("Request body is not valid JSON: " + e.getMessage());
            this.parsedBody = null;
        }
    }

    /**
     * Returns the body as a string
     * @return The request body as a string
     */
    public String getBody() {
        return this.body;
    }

    /**
     * Returns the parsed body as a Map or List
     * @return The parsed body as a Map or List
     */
    public Object parsedBody() {
        return this.parsedBody;
    }
    
    /**
     * Evaluates a JSONPath expression and returns the results as a JSON string
     * @param jsonPath The JSONPath expression to evaluate
     * @return The result as a JSON string
     */
    public String json(String jsonPath) {
        try {
            Object result = JsonPath.read(this.body, jsonPath);
            LOGGER.info("JSON path result: " + result);
            return objectMapper.writeValueAsString(result);
        } catch (Exception e) {
            LOGGER.log(Level.WARNING, "Error in json() function: " + e.getMessage(), e);
            return "null";
        }
    }

    /**
     * Returns a map of all the request parameters
     * @return Map containing path, querystring, and header parameters
     */
    public Map<String, Object> params() {
        Map<String, Object> params = new HashMap<>();
        params.put("path", pathParams);
        params.put("querystring", queryParams);
        params.put("header", headers);
        return params;
    }

    /**
     * Returns the value of a method request parameter from the path, query string, or header value
     * @param paramName The parameter name to look up
     * @return The parameter value or null if not found
     */
    public String params(String paramName) {
        // Check path parameters first
        if (pathParams.containsKey(paramName)) {
            return pathParams.get(paramName);
        }
        
        // Then check query string parameters
        if (queryParams.containsKey(paramName)) {
            return queryParams.get(paramName);
        }
        
        // Finally check header parameters
        if (headers.containsKey(paramName)) {
            return headers.get(paramName);
        }
        
        return null;
    }

    /**
     * Takes a JSONPath expression and returns a JSON object representation of the result
     * @param jsonPath The JSONPath expression to evaluate
     * @return The result as a Java object
     */
    public Object path(String jsonPath) {
        try {
            Object result = JsonPath.read(this.body, jsonPath);
            // Return the result directly without special handling
            return result;
        } catch (Exception e) {
            LOGGER.log(Level.WARNING, "Error in path() function: " + e.getMessage(), e);
            return null;
        }
    }
}
