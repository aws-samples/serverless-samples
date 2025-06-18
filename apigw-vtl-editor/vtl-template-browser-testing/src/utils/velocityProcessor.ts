/**
 * Utility for processing Velocity templates
 */

interface ProcessTemplateResult {
  output: string;
  success: boolean;
  error?: string;
}

/**
 * Process a Velocity template with the given input data
 * @param inputData The input data (JSON object)
 * @param template The Velocity template string
 * @param useApiGatewayContext Whether to use API Gateway context variables
 * @returns The processed template result
 */
export async function processTemplate(
  inputData: any,
  template: string,
  useApiGatewayContext: boolean = false
): Promise<ProcessTemplateResult> {
  try {
    const response = await fetch('/api/process-vtl', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        inputJson: JSON.stringify(inputData),
        template,
        useApiGatewayContext
      })
    });

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Unknown error occurred');
    }

    return {
      output: result.output,
      success: true
    };
  } catch (error: any) {
    return {
      output: '',
      success: false,
      error: error.message
    };
  }
}
