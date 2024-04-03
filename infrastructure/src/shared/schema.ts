import { JsonSchema, JsonSchemaType } from 'aws-cdk-lib/aws-apigateway';

export const SCHEMA_DEBUG: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  description: 'Debugging information for Lambda Function',
  properties: {
    function_url: {
      type: JsonSchemaType.STRING,
      format: 'uri',
      description: 'URL to Lambda Function',
    },
    log_url: {
      type: JsonSchemaType.STRING,
      format: 'uri',
      description: 'URL to CloudWatch Logs',
    },
    trace_url: {
      type: JsonSchemaType.STRING,
      format: 'uri',
      description: 'URL to X-Ray Trace',
    },
  },
  required: [
    'function_url',
    'log_url',
    'trace_url',
  ],
  additionalProperties: false,
};
