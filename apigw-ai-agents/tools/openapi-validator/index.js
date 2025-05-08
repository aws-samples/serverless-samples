// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
// SPDX-License-Identifier: MIT-0

const { Spectral, Document } = require('@stoplight/spectral-core');
const { bundleAndLoadRuleset } = require('@stoplight/spectral-ruleset-bundler/with-loader');
const Parsers = require('@stoplight/spectral-parsers');
const { oas } = require('@stoplight/spectral-rulesets');
// Consider ruleset from https://github.com/andylockran/spectral-aws-apigateway-ruleset

exports.handler = async (event) => {
        // log input
        // console.log('Event: ', event);
        // Initialize Spectral
        const spectral = new Spectral();
        
        // Load the default OpenAPI ruleset
        spectral.setRuleset(oas);
        
        // Parse the input OpenAPI definition
        const openApiDefinition = event.parameters[0].value;
        
        // Create a document for the OpenAPI definition
        const document = new Document(openApiDefinition, Parsers.Yaml, '/input_file');
        
        // Run the validation
        const results = await spectral.run(document);
        // log output
        // console.log('Linter results: ', results);
        
        const response ={
            messageVersion: "1.0",
            response: {
                actionGroup: event.actionGroup,
                function: event.function,
                functionResponse: {
                   responseBody: {
                        "TEXT": { 
                            body: JSON.stringify({
                                validationResults: results.map(result => ({
                                    code: result.code,
                                    path: result.path.join('.'),
                                    message: result.message,
                                    severity: result.severity,
                                    line: result.range.start.line,
                                    character: result.range.start.character
                                }))
                            })
                        }
                    }
                },
                sessionAttributes: event.sessionAttributes,
                promptSessionAttributes: event.promptSessionAttributes
            }
        };
        // log output
        // console.log('Function response: ', response);
        return response;
};