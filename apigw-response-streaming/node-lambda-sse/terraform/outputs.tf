output "chat_endpoint_url" {
  description = "Invoke URL for the SSE chat endpoint"
  value       = "${aws_api_gateway_stage.demo.invoke_url}/chat"
}
