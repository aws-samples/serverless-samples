package com.vtl.processor;

import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.logging.Logger;
import java.util.logging.Level;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.apache.commons.lang.StringEscapeUtils;
/**
 * Utility class to mimic API Gateway's $util variable functionality
 */
public class VelocityUtility {
    private static final Logger LOGGER = Logger.getLogger(VelocityUtility.class.getName());
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    /**
     * Escapes special characters in a string for use in JSON
     */
    public String escapeJavaScript(String input) {
        return StringEscapeUtils.escapeJavaScript(input);
    }
    
    /**
     * URL encodes a string
     */
    public String urlEncode(String input) {
        if (input == null) {
            return null;
        }
        try {
            return java.net.URLEncoder.encode(input, "UTF-8");
        } catch (Exception e) {
            return input;
        }
    }
    
    /**
     * URL decodes a string
     */
    public String urlDecode(String input) {
        if (input == null) {
            return null;
        }
        try {
            return java.net.URLDecoder.decode(input, "UTF-8");
        } catch (Exception e) {
            return input;
        }
    }
    
    /**
     * Base64 encodes a string
     */
    public String base64Encode(String input) {
        if (input == null) {
            return null;
        }
        return Base64.getEncoder().encodeToString(input.getBytes());
    }
    
    /**
     * Base64 decodes a string
     */
    public String base64Decode(String input) {
        if (input == null) {
            return null;
        }
        try {
            return new String(Base64.getDecoder().decode(input));
        } catch (Exception e) {
            return input;
        }
    }
    
    /**
     * Parses a JSON string and returns an object representation
     * This allows accessing and manipulating JSON elements natively in VTL
     * 
     * @param jsonString The JSON string to parse
     * @return An object representation of the JSON that can be used in VTL
     */
    public Object parseJson(String jsonString) {
        if (jsonString == null || jsonString.trim().isEmpty()) {
            return null;
        }
        
        try {
            // First parse as JsonNode
            JsonNode jsonNode = objectMapper.readTree(jsonString);
            
            // Convert JsonNode to Map or List based on the node type
            if (jsonNode.isObject()) {
                return objectMapper.convertValue(jsonNode, Map.class);
            } else if (jsonNode.isArray()) {
                return objectMapper.convertValue(jsonNode, List.class);
            } else {
                // This should not happen based on our assumption
                LOGGER.log(Level.WARNING, "JSON is neither an object nor an array");
                return null;
            }
        } catch (Exception e) {
            LOGGER.log(Level.SEVERE, "Error parsing JSON string: " + jsonString, e);
            return null;
        }
    }
}
