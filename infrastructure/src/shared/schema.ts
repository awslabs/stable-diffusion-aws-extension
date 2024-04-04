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


export const SCHEMA_REQUEST_ID: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Request ID by API Gateway',
  format: 'uuid',
};

export const SCHEMA_LAST_KEY: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'Last Key for Pagination',
};

export const SCHEMA_MESSAGE: JsonSchema = {
  type: JsonSchemaType.STRING,
  description: 'API Operate Message',
};

// API Gateway Validator or Lambda Response
export const SCHEMA_400: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    statusCode: {
      type: JsonSchemaType.INTEGER,
      enum: [
        400,
      ],
    },
    requestId: SCHEMA_REQUEST_ID,
    debug: SCHEMA_DEBUG,
    message: SCHEMA_MESSAGE,
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
    debug: SCHEMA_DEBUG,
    message: {
      type: JsonSchemaType.STRING,
      enum: ['Unauthorized'],
    },
  },
  required: [
    'statusCode',
    'debug',
    'message',
  ],
  additionalProperties: false,
}
;


export const SCHEMA_403: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    requestId: SCHEMA_REQUEST_ID,
    message: {
      type: JsonSchemaType.STRING,
      enum: ['Forbidden'],
    },
  },
  required: [
    'requestId',
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
    requestId: SCHEMA_REQUEST_ID,
    debug: SCHEMA_DEBUG,
    message: SCHEMA_MESSAGE,
  },
  required: [
    'statusCode',
    'requestId',
    'debug',
    'message',
  ],
  additionalProperties: false,
}
;

export const SCHEMA_504: JsonSchema = {
  type: JsonSchemaType.OBJECT,
  properties: {
    message: SCHEMA_MESSAGE,
    requestId: SCHEMA_REQUEST_ID,
  },
  required: [
    'message',
    'requestId',
  ],
  additionalProperties: false,
}

;
