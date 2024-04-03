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


export const SCHEMA_400: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        400,
      ],
    },
    requestId: {
      type: JsonSchemaType.STRING,
      pattern: '^[a-f0-9\\-]{36}$',
    },
    debug: SCHEMA_DEBUG,
    message: {
      type: JsonSchemaType.STRING,
    },
  },
  required: [
    'statusCode',
    'message',
  ],
  additionalProperties: false,
}
;


export const SCHEMA_401: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        401,
      ],
    },
    requestId: {
      type: JsonSchemaType.STRING,
      pattern: '^[a-f0-9\\-]{36}$',
    },
    debug: SCHEMA_DEBUG,
    message: {
      type: JsonSchemaType.STRING,
      enum: ['Unauthorized'],
    },
  },
  required: [
    'statusCode',
    'message',
  ],
  additionalProperties: false,
}
;


export const SCHEMA_403: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    requestId: {
      type: JsonSchemaType.STRING,
      pattern: '^[a-f0-9\\-]{36}$',
    },
    message: {
      type: JsonSchemaType.STRING,
      enum: ['Forbidden'],
    },
  },
  required: [
    'message',
  ],
  additionalProperties: false,
}
;

export const SCHEMA_404: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        404,
      ],
    },
    requestId: {
      type: JsonSchemaType.STRING,
      pattern: '^[a-f0-9\\-]{36}$',
    },
    debug: SCHEMA_DEBUG,
    message: {
      type: JsonSchemaType.STRING,
    },
  },
  required: [
    'message',
  ],
  additionalProperties: false,
}
;

export const SCHEMA_504: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    message: {
      type: JsonSchemaType.STRING,
    },
    requestId: {
      type: JsonSchemaType.STRING,
      format: 'uuid',
    },
  },
  required: [
    'message',
    'requestId',
  ],
  additionalProperties: false,
}

;
