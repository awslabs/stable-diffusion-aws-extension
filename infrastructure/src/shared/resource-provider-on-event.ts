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
import { AttributeDefinition, KeySchemaElement } from '@aws-sdk/client-dynamodb/dist-types/models/models_0';
import {
  GetRoleCommand,
  GetRoleCommandOutput,
  IAMClient,
  ListRolePoliciesCommand,
  PutRolePolicyCommand,
} from '@aws-sdk/client-iam';
import {
  CreateAliasCommand,
  CreateKeyCommand,
  DisableKeyRotationCommand,
  KMSClient,
  ListAliasesCommand,
} from '@aws-sdk/client-kms';
import {
  CreateBucketCommand,
  GetBucketLocationCommand,
  HeadBucketCommand,
  PutBucketCorsCommand,
  S3Client,
} from '@aws-sdk/client-s3';
import { CreateTopicCommand, SNSClient } from '@aws-sdk/client-sns';


const s3Client = new S3Client({});
const ddbClient = new DynamoDBClient({});
const snsClient = new SNSClient({});
const kmsClient = new KMSClient({});
const iamClient = new IAMClient({});


const {
  AWS_REGION,
  ROLE_ARN,
  BUCKET_NAME,
} = process.env;
const partition = AWS_REGION?.startsWith('cn-') ? 'aws-cn' : 'aws';
const accountId = ROLE_ARN?.split(':')[4] || '';

interface Event {
  RequestType: string;
  PhysicalResourceId: string;
}

export async function handler(event: Event, context: Object) {

  console.log(JSON.stringify(event));
  console.log(JSON.stringify(context));

  if (event.RequestType === 'Create') {
    await checkDeploy();
    await createAndCheckResources();
  }

  if (event.RequestType === 'Update') {
    await createAndCheckResources();
  }

  return response(event, true);

}

async function createAndCheckResources() {
  await createBucket();
  await createTables();
  await createKms(
    'sd-extension-password-key',
    'a custom key to encrypt and decrypt password',
  );
  await createTopics();
  await createPolicyForOldRole();
  await waitTableReady('MultiUserTable');
  await putItemUsersTable();
  await waitTableReady('SDInferenceJobTable');
  await createGlobalSecondaryIndex('SDInferenceJobTable');
}

async function waitTableReady(tableName: string) {
  const params = {
    TableName: tableName,
  };

  const command = new DescribeTableCommand(params);
  let isReady = false;
  let count = 0;
  while (!isReady) {
    try {
      const data = await ddbClient.send(command);
      if (data.Table?.TableStatus === 'ACTIVE') {
        isReady = true;
      }
    } catch (err: any) {
      console.log(err);
    }
    if (count > 10) {
      throw new Error(`Table ${tableName} is not ready.`);
    }
    count++;
    console.log(`Waiting for table ${tableName} to be ready ${count}.`);
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
  if (BUCKET_NAME) {
    return BUCKET_NAME;
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
    ModelTable: {
      partitionKey: {
        name: 'id',
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
        name: 'request_id',
        type: AttributeType.STRING,
      },
    },
    ComfyMessageTable: {
      partitionKey: {
        name: 'prompt_id',
        type: AttributeType.STRING,
      },
    },
  };

  for (let tableName in tables) {
    const config = tables[tableName];

    try {
      const KeySchema: KeySchemaElement[] = [
        { AttributeName: config.partitionKey.name, KeyType: 'HASH' },
      ];

      const AttributeDefinitions: AttributeDefinition[] = [
        { AttributeName: config.partitionKey.name, AttributeType: config.partitionKey.type },
      ];

      if (config.sortKey) {
        KeySchema.push({ AttributeName: config.sortKey.name, KeyType: 'RANGE' });
        AttributeDefinitions.push({ AttributeName: config.sortKey.name, AttributeType: config.sortKey.type });
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

async function createGlobalSecondaryIndex(tableName: string) {
  const params: UpdateTableCommandInput = {
    TableName: tableName,
    AttributeDefinitions: [
      {
        AttributeName: 'taskType',
        AttributeType: 'S',
      },
      {
        AttributeName: 'createTime',
        AttributeType: 'S',
      },
    ],
    GlobalSecondaryIndexUpdates: [
      {
        Create: {
          IndexName: 'taskType-createTime-index',
          KeySchema: [
            {
              AttributeName: 'taskType',
              KeyType: 'HASH',
            },
            {
              AttributeName: 'createTime',
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

async function createTopics() {
  const list = [
    'ReceiveSageMakerInferenceSuccess',
    'ReceiveSageMakerInferenceError',
    'successCreateModel',
    'failureCreateModel',
    'StableDiffusionSnsUserTopic',
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

async function createPolicyForOldRole() {
  const name = 'LambdaStartDeployRole';

  try {

    // list policies from role
    const listRolePoliciesCommand = new ListRolePoliciesCommand({
      RoleName: name,
    });
    const listPolicies = await iamClient.send(listRolePoliciesCommand);

    if (!listPolicies.PolicyNames || listPolicies.PolicyNames.includes('LambdaStartDeployPolicy')) {
      return;
    }

    // put policy to the role
    const putRolePolicyCommand = new PutRolePolicyCommand({
      RoleName: name,
      PolicyName: 'LambdaStartDeployPolicy',
      PolicyDocument: JSON.stringify({
        Version: '2012-10-17',
        Statement: [
          {
            Action: [
              'sns:Publish',
              'sns:ListSubscriptionsByTopic',
              'sns:ListTopics',
            ],
            Resource: [
              `arn:${partition}:sns:*:*:StableDiffusionSnsUserTopic`,
              `arn:${partition}:sns:*:*:ReceiveSageMakerInferenceSuccess`,
              `arn:${partition}:sns:*:*:ReceiveSageMakerInferenceError`,
            ],
            Effect: 'Allow',
          },
          {
            Action: [
              's3:Get*',
              's3:List*',
              's3:PutObject',
              's3:GetObject',
            ],
            Resource: [
              `arn:${partition}:s3:::*`,
              `arn:${partition}:s3:::*/*`,
            ],
            Effect: 'Allow',
          },
          {
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
            ],
            Resource: '*',
            Effect: 'Allow',
          },
          {
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
              `arn:${partition}:dynamodb:*:*:table/SDEndpointDeploymentJobTable`,
              `arn:${partition}:dynamodb:*:*:table/MultiUserTable`,
              `arn:${partition}:dynamodb:*:*:table/SDInferenceJobTable`,
            ],
            Effect: 'Allow',
          },
          {
            Action: [
              'logs:CreateLogGroup',
              'logs:CreateLogStream',
              'logs:PutLogEvents',
            ],
            Resource: `arn:${partition}:logs:*:*:log-group:*:*`,
            Effect: 'Allow',
          },
          {
            Action: 'iam:PassRole',
            Resource: `arn:${partition}:iam::*:role/ESDRoleForEndpoint-*`,
            Effect: 'Allow',
          },
        ],
      }),
    });
    await iamClient.send(putRolePolicyCommand);


  } catch (err: any) {
    // it's ok if the role not exists
    if (err?.Error?.Message === `The role with name ${name} cannot be found.`) {
      return;
    }

    if (err?.Error?.Code !== 'NoSuchEntity') {
      console.log(err?.Error?.Code);
      console.log(err?.Error?.Message);
      throw err;
    }

  }

}

async function checkDeploy() {
  const roleName = `ESDRoleForEndpoint-${AWS_REGION}`;

  let resp: GetRoleCommandOutput | undefined = undefined;

  try {

    const getRoleCommand = new GetRoleCommand({
      RoleName: roleName,
    });

    resp = await iamClient.send(getRoleCommand);

  } catch (err: any) {
    console.log(err);
  }

  if (resp && resp.Role) {
    const stackNameTag = resp.Role.Tags?.find(tag => tag.Key === 'stackName');
    if (stackNameTag) {
      throw new Error(`The solution has been deployed in stack: ${stackNameTag.Value}.`);
    }

    throw new Error('The solution has been deployed.');
  }

}
