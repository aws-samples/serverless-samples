# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

output "arn" {
  value       = aws_kms_key.encryption_key.arn
  description = "The ARN of the KMS key"
}