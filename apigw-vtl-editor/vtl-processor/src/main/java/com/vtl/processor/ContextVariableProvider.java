package com.vtl.processor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.HashMap;
import java.util.Map;

/**
 * Provides context variables for API Gateway VTL templates
 */
public class ContextVariableProvider {
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final ObjectNode contextVariables;
    private final ObjectNode stageVariables;
    
    public ContextVariableProvider(JsonNode configNode) {
        this.contextVariables = objectMapper.createObjectNode();
        this.stageVariables = objectMapper.createObjectNode();
        
        if (configNode != null) {
            // Initialize context variables from config
            if (configNode.has("context") && configNode.get("context").isObject()) {
                initializeContextVariables(configNode.get("context"));
            }
            // No default context variables if not provided
            
            // Initialize stage variables from config
            if (configNode.has("stageVariables") && configNode.get("stageVariables").isObject()) {
                initializeStageVariables(configNode.get("stageVariables"));
            }
        }
        // No default context variables if config is null
    }
    
    private void initializeContextVariables(JsonNode contextConfig) {
        // Copy all fields from the context config to the context variables
        contextConfig.fields().forEachRemaining(entry -> {
            if (entry.getValue().isObject()) {
                // For nested objects, create a new object node
                ObjectNode nestedNode = contextVariables.putObject(entry.getKey());
                copyFields(entry.getValue(), nestedNode);
            } else if (entry.getValue().isArray()) {
                // For arrays, copy the array node
                contextVariables.set(entry.getKey(), entry.getValue());
            } else {
                // For simple values, copy the value
                contextVariables.set(entry.getKey(), entry.getValue());
            }
        });
    }
    
    private void copyFields(JsonNode source, ObjectNode target) {
        source.fields().forEachRemaining(entry -> {
            if (entry.getValue().isObject()) {
                // For nested objects, create a new object node and recurse
                ObjectNode nestedNode = target.putObject(entry.getKey());
                copyFields(entry.getValue(), nestedNode);
            } else if (entry.getValue().isArray()) {
                // For arrays, copy the array node
                target.set(entry.getKey(), entry.getValue());
            } else {
                // For simple values, copy the value
                target.set(entry.getKey(), entry.getValue());
            }
        });
    }
    
    private void initializeStageVariables(JsonNode stageVariablesConfig) {
        stageVariablesConfig.fields().forEachRemaining(entry -> {
            stageVariables.set(entry.getKey(), entry.getValue());
        });
    }
    
    public Map<String, Object> getContextVariables() {
        try {
            return objectMapper.convertValue(contextVariables, Map.class);
        } catch (Exception e) {
            return new HashMap<>();
        }
    }
    
    public Map<String, Object> getStageVariables() {
        try {
            return objectMapper.convertValue(stageVariables, Map.class);
        } catch (Exception e) {
            return new HashMap<>();
        }
    }
}
