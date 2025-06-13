package com.vtl.processor;

import java.util.Map;

/**
 * Exception class that carries detailed information about VTL template errors.
 * This is used to attach structured error information to exceptions thrown during
 * VTL template processing.
 */
public class VTLErrorDetailsException extends Exception {
    private final Map<String, Object> errorDetails;
    
    /**
     * Constructor that takes a map of error details
     * @param errorDetails Map containing detailed error information
     */
    public VTLErrorDetailsException(Map<String, Object> errorDetails) {
        super("VTL template processing error");
        this.errorDetails = errorDetails;
    }
    
    /**
     * Get the error details map
     * @return Map containing detailed error information
     */
    public Map<String, Object> getErrorDetails() {
        return errorDetails;
    }
}
