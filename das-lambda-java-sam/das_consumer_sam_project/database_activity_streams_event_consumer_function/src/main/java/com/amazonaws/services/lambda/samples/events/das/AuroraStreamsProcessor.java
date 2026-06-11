package com.amazonaws.services.lambda.samples.events.das;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.zip.GZIPInputStream;
import javax.crypto.spec.SecretKeySpec;

import com.amazonaws.encryptionsdk.AwsCrypto;
import com.amazonaws.encryptionsdk.CommitmentPolicy;
import com.amazonaws.encryptionsdk.CryptoInputStream;
import com.amazonaws.encryptionsdk.jce.JceMasterKey;
import com.amazonaws.services.cloudwatch.model.ResourceNotFoundException;
import com.amazonaws.services.kms.AWSKMS;
import com.amazonaws.services.kms.AWSKMSClientBuilder;
import com.amazonaws.services.kms.model.DecryptRequest;
import com.amazonaws.services.kms.model.DecryptResult;
import com.amazonaws.util.Base64;
import com.amazonaws.util.IOUtils;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.amazonaws.services.lambda.runtime.LambdaLogger;

import com.amazonaws.services.lambda.samples.events.das.models.aurorastreams.PostgresActivity;
import com.amazonaws.services.lambda.samples.events.das.models.aurorastreams.PostgresActivityRecords;;

/**
 * Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not
 * use this file except in compliance with the License. A copy of the License is
 * located at
 *
 * http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 * 
 * This class provides a public method processPostgresActivity that takes the
 * content of an Aurora Database Activity Stream for Aurora Postgres Database.
 * Uses Lambda IAM role for authentication instead of access keys.
 */
public class AuroraStreamsProcessor {

	final String POSTGRES = "postgres";
	final String MYSQL = "mysql";
	final String INVALID_DATABASE_TYPE = "Invalid Database Type";
	String awsRegion;
	AwsCrypto crypto;
	AWSKMS kms;
	Gson gson;

	/**
	 * @param awsRegion - The AWS region in which the Database Activity Stream is
	 *                  created
	 */
	public AuroraStreamsProcessor(String awsRegion) {
		super();
		if (null == awsRegion) {
			awsRegion = "us-east-1";
		}
		try {
			// Use default credential provider chain (Lambda IAM role) instead of access keys
			this.awsRegion = awsRegion;
			this.crypto = AwsCrypto.builder().withCommitmentPolicy(CommitmentPolicy.RequireEncryptAllowDecrypt).build();
			// Use default credentials (Lambda execution role)
			this.kms = AWSKMSClientBuilder.standard().withRegion(awsRegion).build();
			this.gson = new GsonBuilder().serializeNulls().create();
		} catch (Exception e) {
			throw e;
		}
	}

	/**
	 * @return the awsRegion
	 */
	public String getAwsRegion() {
		return awsRegion;
	}

	/**
	 * @param awsRegion the awsRegion to set
	 */
	public void setAwsRegion(String awsRegion) {
		this.awsRegion = awsRegion;
	}

	/**
	 * @param bytes         - The encrypted byte array that contains the Aurora DAS
	 *                      message
	 * @param dbcResourceId - This is the portion of the name of the DAS Kinesis
	 *                      Stream starting with "cluster-". This is needed to match
	 *                      the context of the decryption algorithm with the
	 *                      encrypted message
	 * @param logger        - A reference to the lambda logger to log error messages
	 *                      if any (or for debugging)
	 * @return - An object of class PostgresActivityRecords that replicates the
	 *         structure of a DAS message containing details of a specific database
	 *         activity such as a table creation, row insertion, query etc.
	 */
	public PostgresActivityRecords processPostgresActivity(final ByteBuffer bytes, String dbcResourceId,
			LambdaLogger logger) {
		PostgresActivityRecords processedDatabaseActivity = null;
		try {
			final PostgresActivity activity = gson.fromJson(new String(bytes.array(), StandardCharsets.UTF_8),
					PostgresActivity.class);

			// Base64.Decode
			final byte[] decoded = Base64.decode(activity.getDatabaseActivityEvents());
			final byte[] decodedDataKey = Base64.decode(activity.getKey());

			Map<String, String> context = new HashMap<>();
			context.put("aws:rds:dbc-id", dbcResourceId);

			// Decrypt
			final DecryptRequest decryptRequest = new DecryptRequest()
					.withCiphertextBlob(ByteBuffer.wrap(decodedDataKey)).withEncryptionContext(context);
			final DecryptResult decryptResult = kms.decrypt(decryptRequest);
			final byte[] decrypted = decrypt(decoded, getByteArray(decryptResult.getPlaintext()));

			// GZip Decompress
			final byte[] decompressed = decompress(decrypted);

			// JSON $ActivityRecords
			String processedJson = new String(decompressed, StandardCharsets.UTF_8);
			processedDatabaseActivity = gson.fromJson(processedJson, PostgresActivityRecords.class);

		} catch (Exception e) {
			logger.log(e.getMessage());

		}
		return processedDatabaseActivity;
	}

	/**
	 * @param src - Compressed byte array that needs to be decompressed
	 * @return - Decompressed byte array
	 * @throws IOException
	 */
	private byte[] decompress(final byte[] src) throws IOException {
		ByteArrayInputStream byteArrayInputStream = new ByteArrayInputStream(src);
		GZIPInputStream gzipInputStream = new GZIPInputStream(byteArrayInputStream);
		return IOUtils.toByteArray(gzipInputStream);
	}

	/**
	 * @param decoded        - The encrypted byte array containing the Aurora DAS
	 *                       message
	 * @param decodedDataKey - The encrypted key used to encrypt the Aurora DAS
	 *                       message
	 * @return - The decrypted byte array
	 * @throws IOException
	 */
	private byte[] decrypt(final byte[] decoded, final byte[] decodedDataKey) throws IOException {
		// Create a JCE master key provider using the random key and an AES-GCM
		// encryption algorithm
		final JceMasterKey masterKey = JceMasterKey.getInstance(new SecretKeySpec(decodedDataKey, "AES"), "BC",
				"DataKey", "AES/GCM/NoPadding");
		try (final CryptoInputStream<JceMasterKey> decryptingStream = crypto.createDecryptingStream(masterKey,
				new ByteArrayInputStream(decoded)); final ByteArrayOutputStream out = new ByteArrayOutputStream()) {
			IOUtils.copy(decryptingStream, out);
			return out.toByteArray();
		}
	}

	private static byte[] getByteArray(final ByteBuffer b) {
		byte[] byteArray = new byte[b.remaining()];
		b.get(byteArray);
		return byteArray;
	}

}
