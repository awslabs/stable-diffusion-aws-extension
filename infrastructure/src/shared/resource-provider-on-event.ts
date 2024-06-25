import {
  CreateTableCommand,
  CreateTableCommandInput,
  DescribeTableCommand,
  DynamoDBClient,
  PutItemCommand,
  PutItemCommandInput,
  UpdateTableCommand,
} from '@aws-sdk/client-dynamodb';
import { UpdateTableCommandInput } from '@aws-sdk/client-dynamodb/dist-types/commands/UpdateTableCommand';
import {
  AttributeDefinition,
  KeySchemaElement,
  ScalarAttributeType
} from '@aws-sdk/client-dynamodb/dist-types/models/models_0';
import { CreateRoleCommand, IAMClient, PutRolePolicyCommand } from '@aws-sdk/client-iam';
import {
  CancelKeyDeletionCommand,
  CreateAliasCommand,
  CreateKeyCommand,
  DisableKeyRotationCommand,
  EnableKeyCommand,
  KMSClient,
  ListAliasesCommand,
} from '@aws-sdk/client-kms';
import { CreateBucketCommand, GetBucketLocationCommand, HeadBucketCommand, PutBucketCorsCommand, S3Client } from '@aws-sdk/client-s3';
import { CreateTopicCommand, SNSClient } from '@aws-sdk/client-sns';
import { ESD_ROLE } from './const';
import { CloudWatchClient, PutDashboardCommand } from "@aws-sdk/client-cloudwatch";
const s3Client = new S3Client({});
const ddbClient = new DynamoDBClient({});
const snsClient = new SNSClient({});
const kmsClient = new KMSClient({});
const iamClient = new IAMClient({});
const cwClient = new CloudWatchClient({});

const {
  AWS_REGION,
  ROLE_ARN,
  S3_BUCKET_NAME,
} = process.env;
const accountId = ROLE_ARN?.split(':')[4] || '';

interface Event {
  RequestType: string;
  PhysicalResourceId: string;
}

export async function handler(event: Event, context: Object) {

  console.log(JSON.stringify(event));
  console.log(JSON.stringify(context));

  if (event.RequestType === 'Create') {
    await createAndCheckResources();
  }

  if (event.RequestType === 'Update') {
    await createAndCheckResources();
  }

  return response(event, true);

}

async function createAndCheckResources() {
  await createRegionRole(ESD_ROLE);
  await new Promise(resolve => setTimeout(resolve, 1000));
  // todo will remove in the next major version, current to keep old endpoint
  await createRegionRole(`ESDRoleForEndpoint-${AWS_REGION}`);

  await createBucket();
  await createTables();
  await createKms(
    'sd-extension-password-key',
    'a custom key to encrypt and decrypt password',
  );
  await createTopics();
  await putDashboard();
  await waitTableReady('MultiUserTable');
  await putItemUsersTable();

  await createGlobalSecondaryIndex('SDInferenceJobTable', 'taskType', 'createTime');
  await createGlobalSecondaryIndex('SDEndpointDeploymentJobTable', 'endpoint_name', 'startTime');
}

async function waitTableReady(tableName: string) {
  const params = {
    TableName: tableName,
  };

  const command = new DescribeTableCommand(params);

  while (true) {
    const data = await ddbClient.send(command);

    if (!data.Table) {
      throw new Error(`Table ${tableName} does not exist.`);
    }

    if (data.Table.TableStatus === 'ACTIVE') {
      break;
    }

    console.log(`Table ${tableName} is still in ${data.Table.TableStatus}, Checking again in 1 second...`);

    await new Promise(r => setTimeout(r, 1000));
  }
}


export interface ResourceManagerResponse {
  Result: string;
  BucketName: string;
}

function response(event: Event, isComplete: boolean) {
  return {
    PhysicalResourceId: event.PhysicalResourceId,
    IsComplete: isComplete,
    Data: {
      Result: 'Success',
      BucketName: getBucketName(),
    } as ResourceManagerResponse,
  };
}

function getBucketName() {
  if (S3_BUCKET_NAME) {
    return S3_BUCKET_NAME;
  }

  return `ESD-${accountId}-${AWS_REGION}`;
}

async function createTables() {

  enum AttributeType {
    BINARY = 'B',
    NUMBER = 'N',
    STRING = 'S'
  }

  interface Attribute {
    name: string;
    type: AttributeType;
  }

  interface tableProperties {
    partitionKey: Attribute;
    sortKey?: Attribute;
  }

  const tables: { [key: string]: tableProperties } = {
    SDInferenceJobTable: {
      partitionKey: {
        name: 'InferenceJobId',
        type: AttributeType.STRING,
      },
    },
    MultiUserTable: {
      partitionKey: {
        name: 'kind',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'sort_key',
        type: AttributeType.STRING,
      },
    },
    TrainingTable: {
      partitionKey: {
        name: 'id',
        type: AttributeType.STRING,
      },
    },
    CheckpointTable: {
      partitionKey: {
        name: 'id',
        type: AttributeType.STRING,
      },
    },
    DatasetInfoTable: {
      partitionKey: {
        name: 'dataset_name',
        type: AttributeType.STRING,
      },
    },
    DatasetItemTable: {
      partitionKey: {
        name: 'dataset_name',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'sort_key',
        type: AttributeType.STRING,
      },
    },
    SDEndpointDeploymentJobTable: {
      partitionKey: {
        name: 'EndpointDeploymentJobId',
        type: AttributeType.STRING,
      },
    },
    ComfyWorkflowsTable: {
      partitionKey: {
        name: 'name',
        type: AttributeType.STRING,
      },
    },
    ComfyWorkflowsSchemasTable: {
      partitionKey: {
        name: 'name',
        type: AttributeType.STRING,
      },
    },
    ComfyTemplateTable: {
      partitionKey: {
        name: 'template_name',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'tag',
        type: AttributeType.STRING,
      },
    },
    ComfyConfigTable: {
      partitionKey: {
        name: 'config_name',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'tag',
        type: AttributeType.STRING,
      },
    },
    ComfyExecuteTable: {
      partitionKey: {
        name: 'prompt_id',
        type: AttributeType.STRING,
      },
    },
    ComfySyncTable: {
      partitionKey: {
        name: 'endpoint_name',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'request_time',
        type: AttributeType.NUMBER,
      },
    },
    ComfyInstanceMonitorTable: {
      partitionKey: {
        name: 'endpoint_name',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'gen_instance_id',
        type: AttributeType.STRING,
      },
    },
    ComfyMessageTable: {
      partitionKey: {
        name: 'prompt_id',
        type: AttributeType.STRING,
      },
      sortKey: {
        name: 'request_time',
        type: AttributeType.NUMBER,
      },
    },
  };

  for (let tableName in tables) {
    const config = tables[tableName];

    try {
      const KeySchema: KeySchemaElement[] = [
        {
          AttributeName: config.partitionKey.name,
          KeyType: 'HASH',
        },
      ];

      const AttributeDefinitions: AttributeDefinition[] = [
        {
          AttributeName: config.partitionKey.name,
          AttributeType: config.partitionKey.type,
        },
      ];

      if (config.sortKey) {
        KeySchema.push({
          AttributeName: config.sortKey.name,
          KeyType: 'RANGE',
        });
        AttributeDefinitions.push({
          AttributeName: config.sortKey.name,
          AttributeType: config.sortKey.type,
        });
      }

      const createTableInput: CreateTableCommandInput = {
        TableName: tableName,
        KeySchema: KeySchema,
        AttributeDefinitions: AttributeDefinitions,
        BillingMode: 'PAY_PER_REQUEST',
      };
      const createTableCommand = new CreateTableCommand(createTableInput);
      await ddbClient.send(createTableCommand);
      console.log(`Table ${tableName} created.`);
    } catch (err: any) {
      if (err.message !== `Table already exists: ${tableName}`) {
        throw err;
      }
      console.log(err.message);
    }
  }

}

async function putItemUsersTable() {

  await putItem('MultiUserTable', {
    kind: { S: 'role' },
    sort_key: { S: 'IT Operator' },
    creator: { S: 'ESD' },
    permissions: {
      L: [
        { S: 'train:all' },
        { S: 'checkpoint:all' },
        { S: 'inference:all' },
        { S: 'sagemaker_endpoint:all' },
        { S: 'user:all' },
        { S: 'role:all' },
      ],
    },
  });

  await putItem('MultiUserTable', {
    kind: { S: 'role' },
    sort_key: { S: 'byoc' },
    creator: { S: 'ESD' },
    permissions: {
      L: [
        { S: 'train:all' },
        { S: 'checkpoint:all' },
        { S: 'inference:all' },
        { S: 'sagemaker_endpoint:all' },
        { S: 'user:all' },
        { S: 'role:all' },
      ],
    },
  });

  await putItem('MultiUserTable', {
    kind: { S: 'user' },
    sort_key: { S: 'api' },
    creator: { S: 'ESD' },
    roles: {
      L: [
        {
          S: 'IT Operator',
        },
      ],
    },
  });

}

async function putItem(tableName: string, item: any) {
  try {
    const putItemCommandInput: PutItemCommandInput = {
      TableName: tableName,
      Item: item,
    };
    const putItemCommand = new PutItemCommand(putItemCommandInput);
    await ddbClient.send(putItemCommand);
    console.log(`putItem ${tableName} Success`);
    console.log(item);
  } catch (err: any) {
    console.log(`putItem ${tableName} Error`, err);
  }
}

async function createGlobalSecondaryIndex(tableName: string, pk: string, sk: string, skt: ScalarAttributeType = 'S') {

  await waitTableReady(tableName);

  const params: UpdateTableCommandInput = {
    TableName: tableName,
    AttributeDefinitions: [
      {
        AttributeName: pk,
        AttributeType: 'S',
      },
      {
        AttributeName: sk,
        AttributeType: skt,
      },
    ],
    GlobalSecondaryIndexUpdates: [
      {
        Create: {
          IndexName: `${pk}-${sk}-index`,
          KeySchema: [
            {
              AttributeName: pk,
              KeyType: 'HASH',
            },
            {
              AttributeName: sk,
              KeyType: 'RANGE',
            },
          ],
          Projection: {
            ProjectionType: 'ALL',
          },
        },
      },
    ],
  };

  try {
    const command = new UpdateTableCommand(params);
    // eslint-disable-next-line @typescript-eslint/no-shadow
    const response = await ddbClient.send(command);
    console.log('createGlobalSecondaryIndex Success', response);
  } catch (err) {
    console.log('createGlobalSecondaryIndex Error', err);
  }
}

async function createBucket() {
  const bucketName = getBucketName();
  let createNew = false;
  try {

    const createBucketCommand = new CreateBucketCommand({
      Bucket: bucketName,
      ACL: 'private',
    });

    await s3Client.send(createBucketCommand);
    createNew = true;

    console.log(`Bucket ${bucketName} created.`);

  } catch (err: any) {

    if (err.Code === 'BucketAlreadyOwnedByYou') {
      console.log(`Bucket ${bucketName} exists.`);
    } else if (err.Code === 'BucketAlreadyExists') {
      console.log(`Bucket ${bucketName} exists.`);
      throw new Error(`${err.message}`);
    } else {
      throw err;
    }

  }

  if (createNew) {
    await putBucketCors(bucketName);
  } else {
    await checkBucketLocation();
    await checkBucketPermission(bucketName);
  }

}

async function checkBucketPermission(bucketName: string) {
  try {
    const headBucketCommand = new HeadBucketCommand({ Bucket: bucketName });
    await s3Client.send(headBucketCommand);
  } catch (err: any) {
    console.log(err);
    throw new Error(`bucket ${bucketName} permission check failed.`);
  }
}

async function checkBucketLocation() {
  const bucketName = getBucketName();
  const bucketLocation = await s3Client.send(new GetBucketLocationCommand({
    Bucket: bucketName,
  }));

  if (!bucketLocation.LocationConstraint) {
    throw new Error(`Can not get bucket ${bucketName} location. GetBucketLocationCommandOutput is ${JSON.stringify(bucketLocation)}`);
  }

  if (bucketLocation.LocationConstraint !== AWS_REGION) {
    throw new Error(`Bucket ${bucketName} must be in ${AWS_REGION}, but it's in ${bucketLocation.LocationConstraint}.`);
  }

}

async function putBucketCors(bucketName: string) {
  const putBucketCorsCommand = new PutBucketCorsCommand({
    Bucket: bucketName,
    CORSConfiguration: {
      CORSRules: [
        {
          AllowedHeaders: ['*'],
          AllowedMethods: ['PUT', 'HEAD', 'GET'],
          AllowedOrigins: ['*'],
          ExposeHeaders: ['ETag'],
        },
      ],
    },
  });

  await s3Client.send(putBucketCorsCommand);
}

async function putDashboard() {

    const last_build_time = new Date().toISOString();
    const dashboardBody = {
          'widgets': [
            {
              'height': 2,
              'width': 24,
              'y': 0,
              'x': 0,
              'type': 'text',
              'properties': {
                'markdown': `## ESD (Extension for Stable Diffusion on AWS) \n Last Build Time: ${last_build_time}`,
              },
            },
            {
              'height': 4,
              'width': 16,
              'y': 26,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'EndpointReadySeconds',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'stacked': false,
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'Comfy-EndpointReadySeconds',
                'view': 'singleValue',
                'yAxis': {
                  'left': {
                    'min': 0,
                    'max': 100,
                  },
                },
              },
            },
            {
              'height': 4,
              'width': 16,
              'y': 39,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'EndpointReadySeconds',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'title': 'SD-EndpointReadySeconds',
                'period': 300,
                'stat': 'Maximum',
                'yAxis': {
                  'left': {
                    'min': 0,
                    'max': 100,
                  },
                },
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 18,
              'x': 12,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'DownloadFileSeconds',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'Comfy-DownloadFileSeconds',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 18,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'InstanceInitSeconds',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'Comfy-InstanceInitSeconds',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 22,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'DecompressFileSeconds',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'title': 'Comfy-DecompressFileSeconds',
                'period': 300,
                'stat': 'Maximum',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 31,
              'x': 12,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'DownloadFileSeconds',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'SD-DownloadFileSeconds',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 31,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'InstanceInitSeconds',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'SD-InstanceInitSeconds',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 35,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'DecompressFileSeconds',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'SD-DecompressFileSeconds',
              },
            },
            {
              'height': 4,
              'width': 9,
              'y': 10,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'InferenceTotal',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '.',
                    'InferenceEndpointReceived',
                    '.',
                    '.',
                  ],
                  [
                    '.',
                    'InferenceSucceed',
                    '.',
                    '.',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Sum',
                'title': 'SD-Inference',
                'stacked': false,
              },
            },
            {
              'height': 4,
              'width': 15,
              'y': 10,
              'x': 9,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'InferenceLatency',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'p99',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Maximum',
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Average',
                'stacked': false,
                'title': 'SD-InferenceLatency',
              },
            },
            {
              'height': 4,
              'width': 9,
              'y': 2,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'InferenceTotal',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '.',
                    'InferenceEndpointReceived',
                    '.',
                    '.',
                  ],
                  [
                    '.',
                    'InferenceSucceed',
                    '.',
                    '.',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'title': 'Comfy-Inference',
                'period': 300,
                'stat': 'Sum',
              },
            },
            {
              'height': 4,
              'width': 15,
              'y': 2,
              'x': 9,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'InferenceLatency',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'stat': 'p99',
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Maximum',
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'stat': 'Average',
                'period': 300,
                'title': 'Comfy-InferenceLatency',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 35,
              'x': 12,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'UploadEndpointCacheSeconds',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Maximum',
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Average',
                'title': 'SD-UploadEndpointCacheSeconds',
              },
            },
            {
              'height': 4,
              'width': 12,
              'y': 22,
              'x': 12,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'UploadEndpointCacheSeconds',
                    'Service',
                    'Comfy',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Maximum',
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'title': 'Comfy-UploadEndpointCacheSeconds',
                'period': 300,
                'stat': 'Average',
              },
            },
            {
              'height': 4,
              'width': 8,
              'y': 39,
              'x': 16,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'DownloadFileSize',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'SD-DownloadFileSize',
              },
            },
            {
              'height': 4,
              'width': 24,
              'y': 44,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'TrainingLatency',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'stat': 'p99',
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Maximum',
                    },
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 900,
                'stat': 'Average',
                'title': 'TrainingLatency',
              },
            },
            {
              'height': 4,
              'width': 8,
              'y': 26,
              'x': 16,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'DownloadFileSize',
                    'Service',
                    'Comfy',
                    {
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                  ],
                ],
                'sparkline': true,
                'view': 'singleValue',
                'region': AWS_REGION,
                'stat': 'Maximum',
                'period': 300,
                'title': 'Comfy-DownloadFileSize',
              },
            },
            {
              'height': 4,
              'width': 24,
              'y': 14,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'QueueLatency',
                    'Service',
                    'Stable-Diffusion',
                    {
                      'region': AWS_REGION,
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'p99',
                    },
                  ],
                  [
                    '...',
                    {
                      'region': AWS_REGION,
                      'stat': 'Maximum',
                    },
                  ],
                ],
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Average',
                'title': 'SDQueueLatency',
              },
            },
            {
              'height': 4,
              'width': 24,
              'y': 6,
              'x': 0,
              'type': 'metric',
              'properties': {
                'metrics': [
                  [
                    'ESD',
                    'QueueLatency',
                    'Service',
                    'Comfy',
                    {
                      'stat': 'Minimum',
                    },
                  ],
                  [
                    '...',
                    {
                      'stat': 'Average',
                    },
                  ],
                  [
                    '...',
                    {
                      'stat': 'p99',
                    },
                  ],
                  [
                    '...',
                  ],
                ],
                'view': 'singleValue',
                'region': AWS_REGION,
                'period': 300,
                'stat': 'Maximum',
                'title': 'ComfyQueueLatency',
              },
            },
          ],
        }
    ;

    const putDashboardCommand = new PutDashboardCommand({
      DashboardName: 'ESD',
      DashboardBody: JSON.stringify(dashboardBody),
    });

    await cwClient.send(putDashboardCommand);

    console.log(`Dashboard ESD created.`);

}

async function createTopics() {
  const list = [
    // SD
    'ReceiveSageMakerInferenceSuccess',
    'ReceiveSageMakerInferenceError',
    'StableDiffusionSnsUserTopic',
    // comfy
    'comfyExecuteFail',
    'comfyExecuteSuccess',
  ];

  for (let Name of list) {

    const createTopicCommand = new CreateTopicCommand({ Name });
    await snsClient.send(createTopicCommand);

    console.log(`Topic ${Name} created.`);
  }

}

async function createKms(aliasName: string, description: string) {

  const alias = `alias/${aliasName}`;

  // query kms key by aliasName, if exists, return true
  if (await findKeyByAlias(alias)) {
    console.log(`Kms ${alias} exists.`);
    return true;
  }

  // create kms key and set Alias by aws sdk
  const createKeyCommand = new CreateKeyCommand({
    KeyUsage: 'ENCRYPT_DECRYPT',
    Description: description,
  });
  const key = await kmsClient.send(createKeyCommand);

  const disableKeyRotationCommand = new DisableKeyRotationCommand({
    KeyId: key.KeyMetadata?.KeyId,
  });
  await kmsClient.send(disableKeyRotationCommand);


  const createAliasCommand = new CreateAliasCommand({
    AliasName: alias,
    TargetKeyId: key?.KeyMetadata?.KeyId,
  });
  await kmsClient.send(createAliasCommand);

  // the key maybe pending deletion, so cancel and enable it
  try {
    const cancelKeyDeletionCommand = new CancelKeyDeletionCommand({
      KeyId: key.KeyMetadata?.KeyId,
    });
    await kmsClient.send(cancelKeyDeletionCommand);
  } catch (err: any) {
    console.log(err);
  }

  try {
    const enableKeyCommand = new EnableKeyCommand({
      KeyId: key.KeyMetadata?.KeyId,
    });
    await kmsClient.send(enableKeyCommand);
  } catch (err: any) {
    console.log(err);
  }

  console.log(`Kms ${aliasName} created.`);
  return true;

}

async function findKeyByAlias(aliasName: string) {
  let nextToken = undefined;
  do {
    const command: ListAliasesCommand = new ListAliasesCommand({ Marker: nextToken });
    const resp = await kmsClient.send(command);
    const alias = resp.Aliases?.find(
      a => a.AliasName === aliasName,
    );
    if (alias) {
      return alias.TargetKeyId;
    }
    nextToken = resp.NextMarker;
  } while (nextToken);

  return null;
}

async function createRegionRole(role_name: string) {

  console.log(`Creating role ${role_name}`);

  try {

    const assumedRolePolicy = JSON.stringify({
      Version: '2012-10-17',
      Statement: [
        {
          Effect: 'Allow',
          Principal: {
            Service: ['lambda.amazonaws.com', 'sagemaker.amazonaws.com'],
          },
          Action: 'sts:AssumeRole',
        },
      ],
    });
    await iamClient.send(new CreateRoleCommand({
      RoleName: role_name,
      AssumeRolePolicyDocument: assumedRolePolicy,
    }));

    // Define policy documents for each service
    const snsPolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          'sns:Publish',
          'sns:ListSubscriptionsByTopic',
          'sns:ListTopics',
        ],
        Resource: [
          '*',
        ],
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'SnsPolicy',
      PolicyDocument: snsPolicyDocument,
    }));

    const s3PolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          's3:Get*',
          's3:List*',
          's3:PutObject',
          's3:GetObject',
        ],
        Resource: '*',
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'S3Policy',
      PolicyDocument: s3PolicyDocument,
    }));

    const endpointPolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          'sagemaker:DeleteModel',
          'sagemaker:DeleteEndpoint',
          'sagemaker:DescribeEndpoint',
          'sagemaker:DeleteEndpointConfig',
          'sagemaker:DescribeEndpointConfig',
          'sagemaker:InvokeEndpoint',
          'sagemaker:CreateModel',
          'sagemaker:CreateEndpoint',
          'sagemaker:CreateEndpointConfig',
          'sagemaker:InvokeEndpointAsync',
          'ecr:GetAuthorizationToken',
          'ecr:BatchCheckLayerAvailability',
          'ecr:GetDownloadUrlForLayer',
          'ecr:GetRepositoryPolicy',
          'ecr:DescribeRepositories',
          'ecr:ListImages',
          'ecr:DescribeImages',
          'ecr:BatchGetImage',
          'ecr:InitiateLayerUpload',
          'ecr:UploadLayerPart',
          'ecr:CompleteLayerUpload',
          'ecr:PutImage',
          'cloudwatch:PutMetricAlarm',
          'cloudwatch:PutMetricData',
          'cloudwatch:DeleteAlarms',
          'cloudwatch:DescribeAlarms',
          'sagemaker:UpdateEndpointWeightsAndCapacities',
          'iam:CreateServiceLinkedRole',
          'iam:PassRole',
          'sts:AssumeRole',
          'xray:PutTraceSegments',
          'xray:PutTelemetryRecords',
        ],
        Resource: [
          '*',
        ],
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'EndpointPolicy',
      PolicyDocument: endpointPolicyDocument,
    }));

    const dynamoDBPolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          'dynamodb:Query',
          'dynamodb:GetItem',
          'dynamodb:PutItem',
          'dynamodb:DeleteItem',
          'dynamodb:UpdateItem',
          'dynamodb:Describe*',
          'dynamodb:List*',
          'dynamodb:Scan',
        ],
        Resource: [
          '*',
        ],
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'DdbPolicy',
      PolicyDocument: dynamoDBPolicyDocument,
    }));

    const logPolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        Resource: [
          '*',
        ],
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'LogPolicy',
      PolicyDocument: logPolicyDocument,
    }));

    const sqsPolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          'sqs:SendMessage',
        ],
        Resource: [
          '*',
        ],
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'SqsPolicy',
      PolicyDocument: sqsPolicyDocument,
    }));

    const passRolePolicyDocument = JSON.stringify({
      Version: '2012-10-17',
      Statement: [{
        Effect: 'Allow',
        Action: [
          'iam:PassRole',
        ],
        Resource: [
          '*',
        ],
      }],
    });
    await iamClient.send(new PutRolePolicyCommand({
      RoleName: role_name,
      PolicyName: 'PassRolePolicy',
      PolicyDocument: passRolePolicyDocument,
    }));

  } catch (err: any) {

    console.log(err);

    if (err?.Error?.Code !== 'EntityAlreadyExists') {
      console.log(err?.Error?.Code);
      console.log(err?.Error?.Message);
      throw err;
    }

  }

}
