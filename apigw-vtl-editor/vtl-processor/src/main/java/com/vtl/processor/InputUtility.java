package com.vtl.processor;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Utility class to mimic API Gateway's $input variable functionality
 */
public class InputUtility {
    private final JsonNode rootNode;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public InputUtility(JsonNode rootNode) {
        this.rootNode = rootNode;
    }

    /**
     * Mimics the $input.path('$') functionality in API Gateway
     * @param path The JSON path expression
     * @return The value at the specified path
     */
    public Object path(String path) {
        try {
            if (path == null || path.isEmpty()) {
                return null;
            }

            // Handle the root path case
            if (path.equals("$")) {
                return convertJsonNodeToObject(rootNode);
            }

            // Remove the leading $ if present
            if (path.startsWith("$")) {
                path = path.substring(1);
            }

            // Remove leading dot if present
            if (path.startsWith(".")) {
                path = path.substring(1);
            }

            // Split the path into segments
            String[] segments = path.split("\\.");
            JsonNode currentNode = rootNode;

            // Navigate through the path
            for (String segment : segments) {
                if (currentNode == null) {
                    return null;
                }

                // Handle array access with [index]
                if (segment.contains("[") && segment.endsWith("]")) {
                    String fieldName = segment.substring(0, segment.indexOf("["));
                    String indexStr = segment.substring(segment.indexOf("[") + 1, segment.length() - 1);
                    
                    try {
                        int index = Integer.parseInt(indexStr);
                        
                        if (!fieldName.isEmpty()) {
                            currentNode = currentNode.get(fieldName);
                            if (currentNode == null || !currentNode.isArray()) {
                                return null;
                            }
                        }
                        
                        if (currentNode.isArray() && index >= 0 && index < currentNode.size()) {
                            currentNode = currentNode.get(index);
                        } else {
                            return null;
                        }
                    } catch (NumberFormatException e) {
                        return null;
                    }
                } else {
                    currentNode = currentNode.get(segment);
                    if (currentNode == null) {
                        return null;
                    }
                }
            }

            return convertJsonNodeToObject(currentNode);
        } catch (Exception e) {
            // Return a descriptive error message that can help with debugging
            return "Error accessing path '" + path + "': " + e.getMessage();
        }
    }

    /**
     * Converts a JsonNode to a Java object
     */
    private Object convertJsonNodeToObject(JsonNode node) {
        if (node == null) {
            return null;
        }
        
        if (node.isNull()) {
            return null;
        } else if (node.isTextual()) {
            return node.asText();
        } else if (node.isInt()) {
            return node.asInt();
        } else if (node.isLong()) {
            return node.asLong();
        } else if (node.isDouble()) {
            return node.asDouble();
        } else if (node.isBoolean()) {
            return node.asBoolean();
        } else if (node.isArray()) {
            List<Object> list = new ArrayList<>();
            ArrayNode arrayNode = (ArrayNode) node;
            for (JsonNode element : arrayNode) {
                list.add(convertJsonNodeToObject(element));
            }
            return list;
        } else if (node.isObject()) {
            Map<String, Object> map = new HashMap<>();
            ObjectNode objectNode = (ObjectNode) node;
            objectNode.fields().forEachRemaining(entry -> {
                map.put(entry.getKey(), convertJsonNodeToObject(entry.getValue()));
            });
            return map;
        } else {
            return node.toString();
        }
    }
    
    /**
     * Returns the JSON as a string
     * This is the critical method that needs to return proper JSON, not Java Map format
     */
    public String json(String path) {
        try {
            Object result = path(path);
            if (result == null) {
                return "null";
            }
            
            // If the result is already a string and looks like JSON, return it directly
            if (result instanceof String) {
                String strResult = (String) result;
                if ((strResult.startsWith("{") && strResult.endsWith("}")) || 
                    (strResult.startsWith("[") && strResult.endsWith("]"))) {
                    return strResult;
                }
            }
            
            // Otherwise, convert the object to proper JSON
            return objectMapper.writeValueAsString(result);
        } catch (JsonProcessingException e) {
            // If JSON conversion fails, return a JSON error object
            return "{\"error\":\"Failed to convert to JSON: " + e.getMessage() + "\"}";
        }
    }
    
    /**
     * Returns the JSON as a string with indentation
     */
    public String jsonWithIndentation(String path) {
        try {
            Object result = path(path);
            if (result == null) {
                return "null";
            }
            
            // Convert the object to proper JSON with indentation
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(result);
        } catch (JsonProcessingException e) {
            // If JSON conversion fails, return a JSON error object
            return "{\"error\":\"Failed to convert to JSON: " + e.getMessage() + "\"}";
        }
    }
}
