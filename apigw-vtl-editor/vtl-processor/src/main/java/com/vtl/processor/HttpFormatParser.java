package com.vtl.processor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.HashMap;
import java.util.Map;
import java.util.logging.Logger;
import java.util.logging.Level;

/**
 * Parses HTTP request format into components needed for API Gateway simulation
 */
public class HttpFormatParser {
    private static final Logger LOGGER = Logger.getLogger(HttpFormatParser.class.getName());
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    /**
     * Parse an HTTP request string into its components
     * 
     * @param httpRequest The HTTP request string
     * @return A JsonNode containing the parsed components
     */
    public JsonNode parseHttpRequest(String httpRequest) throws Exception {
        try {
            String[] lines = httpRequest.split("\\r?\\n");
            
            if (lines.length == 0) {
                throw new Exception("Invalid HTTP request: empty request");
            }
            
            // Parse request line
            String requestLine = lines[0];
            String[] requestLineParts = requestLine.split(" ");
            
            if (requestLineParts.length < 2) {
                throw new Exception("Invalid HTTP request line: " + requestLine);
            }
            
            String method = requestLineParts[0];
            String pathWithQuery = requestLineParts[1];
            
            // Parse path and query parameters
            String path = pathWithQuery;
            String queryString = "";
            
            if (pathWithQuery.contains("?")) {
                String[] pathParts = pathWithQuery.split("\\?", 2);
                path = pathParts[0];
                queryString = pathParts[1];
            }
            
            // Parse query parameters
            ObjectNode queryParams = objectMapper.createObjectNode();
            if (!queryString.isEmpty()) {
                String[] params = queryString.split("&");
                for (String param : params) {
                    String[] keyValue = param.split("=", 2);
                    String key = keyValue[0];
                    String value = keyValue.length > 1 ? keyValue[1] : "";
                    queryParams.put(key, value);
                }
            }
            
            // Parse headers
            ObjectNode headers = objectMapper.createObjectNode();
            int i = 1;
            while (i < lines.length && !lines[i].trim().isEmpty()) {
                String headerLine = lines[i];
                int colonIndex = headerLine.indexOf(':');
                
                if (colonIndex > 0) {
                    String key = headerLine.substring(0, colonIndex).trim();
                    String value = headerLine.substring(colonIndex + 1).trim();
                    headers.put(key, value);
                }
                
                i++;
            }
            
            // Parse body
            StringBuilder bodyBuilder = new StringBuilder();
            if (i < lines.length) {
                i++; // Skip the empty line after headers
                
                while (i < lines.length) {
                    bodyBuilder.append(lines[i]);
                    if (i < lines.length - 1) {
                        bodyBuilder.append("\n");
                    }
                    i++;
                }
            }
            
            String body = bodyBuilder.toString().trim();
            
            // Create result object
            ObjectNode result = objectMapper.createObjectNode();
            result.put("method", method);
            result.put("path", path);
            result.set("headers", headers);
            result.set("queryParams", queryParams);
            result.set("pathParams", objectMapper.createObjectNode()); // Empty for now
            result.put("body", body);
            LOGGER.info("Body before returning from parseHttpRequest: " + body);
            return result;
        } catch (Exception e) {
            throw new Exception("Error parsing HTTP request: " + e.getMessage(), e);
        }
    }
}
