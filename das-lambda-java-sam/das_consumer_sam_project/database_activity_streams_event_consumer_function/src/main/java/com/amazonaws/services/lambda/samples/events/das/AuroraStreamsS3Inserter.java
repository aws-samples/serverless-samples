package com.amazonaws.services.lambda.samples.events.das;

import java.util.UUID;

import software.amazon.awssdk.awscore.exception.AwsServiceException;
import software.amazon.awssdk.core.exception.SdkClientException;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.regions.providers.DefaultAwsRegionProviderChain;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.ChecksumAlgorithm;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.model.S3Exception;

public class AuroraStreamsS3Inserter {
	String s3Bucket;
	String s3Prefix;
	S3Client s3Client;
	
	/**
	 * @param s3Bucket
	 * @param s3Prefix
	 */
	public AuroraStreamsS3Inserter(String s3Bucket, String s3Prefix) {
		super();
		this.s3Bucket = s3Bucket;
		this.s3Prefix = s3Prefix;
		DefaultAwsRegionProviderChain defaultAwsRegionProviderChain = new DefaultAwsRegionProviderChain();
		Region region = defaultAwsRegionProviderChain.getRegion();
		s3Client = S3Client.builder().region(region).build();
	}
	/**
	 * @return the s3Bucket
	 */
	public String getS3Bucket() {
		return s3Bucket;
	}
	/**
	 * @param s3Bucket the s3Bucket to set
	 */
	public void setS3Bucket(String s3Bucket) {
		this.s3Bucket = s3Bucket;
	}
	/**
	 * @return the s3Prefix
	 */
	public String getS3Prefix() {
		return s3Prefix;
	}
	/**
	 * @param s3Prefix the s3Prefix to set
	 */
	public void setS3Prefix(String s3Prefix) {
		this.s3Prefix = s3Prefix;
	}
	/**
	 * @return the s3Client
	 */
	public S3Client getS3Client() {
		return s3Client;
	}
	/**
	 * @param s3Client the s3Client to set
	 */
	public void setS3Client(S3Client s3Client) {
		this.s3Client = s3Client;
	}
	
	/**
	 * Insert data into S3 with retry logic and exponential backoff
	 * Implements 3 retry attempts with exponential backoff for VPC endpoint connectivity issues
	 * 
	 * @param objectData The data to write to S3
	 * @throws AwsServiceException If S3 service error occurs after all retries
	 * @throws SdkClientException If client error occurs after all retries
	 */
	public void insertIntoS3(String objectData) throws AwsServiceException, SdkClientException {
		final int MAX_RETRIES = 3;
		final long INITIAL_BACKOFF_MS = 100;
		
		String objectKey = UUID.randomUUID().toString();
		String s3ObjectKey = "";
		if ("".equals(s3Prefix)) {
			s3ObjectKey = objectKey;
		} else if (s3Prefix.endsWith("/")) {
			s3ObjectKey = s3Prefix + objectKey;
		} else {
			s3ObjectKey = s3Prefix + "/" + objectKey;
		}
		
		// Add checksum algorithm for S3 Object Lock compatibility
		// SHA256 checksum is required when Object Lock is enabled on the bucket
		PutObjectRequest objectRequest = PutObjectRequest.builder()
				                                         .bucket(s3Bucket)
				                                         .key(s3ObjectKey)
				                                         .checksumAlgorithm(ChecksumAlgorithm.SHA256)
				                                         .build();
		
		// Retry logic with exponential backoff
		int attempt = 0;
		Exception lastException = null;
		
		while (attempt < MAX_RETRIES) {
			try {
				s3Client.putObject(objectRequest, RequestBody.fromString(objectData));
				// Success - return immediately
				return;
			} catch (S3Exception e) {
				lastException = e;
				attempt++;
				
				// Check if this is a retryable error
				if (isRetryableException(e) && attempt < MAX_RETRIES) {
					long backoffTime = INITIAL_BACKOFF_MS * (long) Math.pow(2, attempt - 1);
					System.err.println(String.format(
						"S3 write failed (attempt %d/%d) for key %s. Error: %s. Retrying in %d ms...",
						attempt, MAX_RETRIES, s3ObjectKey, e.getMessage(), backoffTime
					));
					
					try {
						Thread.sleep(backoffTime);
					} catch (InterruptedException ie) {
						Thread.currentThread().interrupt();
						throw SdkClientException.builder()
							.message("Retry interrupted")
							.cause(ie)
							.build();
					}
				} else {
					// Non-retryable error or max retries reached
					System.err.println(String.format(
						"S3 write failed permanently for key %s after %d attempts. Error: %s",
						s3ObjectKey, attempt, e.getMessage()
					));
					throw e;
				}
			} catch (SdkClientException e) {
				lastException = e;
				attempt++;
				
				// VPC endpoint connectivity issues typically manifest as SdkClientException
				if (attempt < MAX_RETRIES) {
					long backoffTime = INITIAL_BACKOFF_MS * (long) Math.pow(2, attempt - 1);
					System.err.println(String.format(
						"S3 VPC endpoint connectivity issue (attempt %d/%d) for key %s. Error: %s. Retrying in %d ms...",
						attempt, MAX_RETRIES, s3ObjectKey, e.getMessage(), backoffTime
					));
					
					try {
						Thread.sleep(backoffTime);
					} catch (InterruptedException ie) {
						Thread.currentThread().interrupt();
						throw SdkClientException.builder()
							.message("Retry interrupted")
							.cause(ie)
							.build();
					}
				} else {
					System.err.println(String.format(
						"S3 VPC endpoint connectivity failed permanently for key %s after %d attempts. Error: %s",
						s3ObjectKey, attempt, e.getMessage()
					));
					throw e;
				}
			}
		}
		
		// This should not be reached, but handle it just in case
		if (lastException instanceof AwsServiceException) {
			throw (AwsServiceException) lastException;
		} else if (lastException instanceof SdkClientException) {
			throw (SdkClientException) lastException;
		} else {
			throw SdkClientException.builder()
				.message("S3 write failed after " + MAX_RETRIES + " attempts")
				.cause(lastException)
				.build();
		}
	}
	
	/**
	 * Determine if an S3Exception is retryable
	 * 
	 * @param e The S3Exception to check
	 * @return true if the exception is retryable, false otherwise
	 */
	private boolean isRetryableException(S3Exception e) {
		// Retry on throttling, service unavailable, and internal errors
		int statusCode = e.statusCode();
		return statusCode == 429 ||  // Too Many Requests
		       statusCode == 500 ||  // Internal Server Error
		       statusCode == 502 ||  // Bad Gateway
		       statusCode == 503 ||  // Service Unavailable
		       statusCode == 504;    // Gateway Timeout
	}
}
