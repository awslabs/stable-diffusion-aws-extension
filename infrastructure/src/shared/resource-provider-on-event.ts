import {CreateTableCommand, CreateTableCommandInput, DynamoDBClient} from '@aws-sdk/client-dynamodb';
import {AttributeDefinition, KeySchemaElement} from '@aws-sdk/client-dynamodb/dist-types/models/models_0';
import {IAMClient, ListRolePoliciesCommand, PutRolePolicyCommand} from '@aws-sdk/client-iam';
import {
    CreateAliasCommand,
    CreateKeyCommand,
    DisableKeyRotationCommand,
    KMSClient,
    ListAliasesCommand,
} from '@aws-sdk/client-kms';
import {CreateBucketCommand, HeadBucketCommand, S3Client} from '@aws-sdk/client-s3';
import {CreateTopicCommand, SNSClient} from '@aws-sdk/client-sns';


const s3Client = new S3Client({});
const ddbClient = new DynamoDBClient({});
const snsClient = new SNSClient({});
const kmsClient = new KMSClient({});
const iamClient = new IAMClient({});


export async function handler(event: any, context: Object) {

    console.log(JSON.stringify(event));
    console.log(JSON.stringify(context));

    if (event.routeKey) {
        event = {
            RequestType: 'Create',
            PhysicalResourceId: 'test',
            ResourceProperties: {
                bucketName: 'elonniu'
            }
        }
    }

    switch (event.RequestType) {
        case 'Create':
            return changeResource(event);
        case 'Update':
            return changeResource(event);
        case 'Delete':
            return response(event, true);
        default:
            throw new Error(`Invalid request type: ${event.RequestType}`);
    }

    // const {BucketName} = event.OldResourceProperties;
}

async function changeResource(event: any) {
    await createDdbTable();
    await createBucket(event);
    await createKms('sd-extension-password-key', 'a custom key for sd extension to encrypt and decrypt password');
    await createKms('sd-extension-topic-key', 'a custom key for sd extension to encrypt and decrypt topic');
    await createTopics();
    await createRole();
    return response(event, true);
}

function response(event: any, message: boolean) {
    return {
        PhysicalResourceId: event.PhysicalResourceId,
        // IsComplete: true,
        Data: {
            Response: message,
        },
    };
}

async function createDdbTable() {

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
        SDInferenceJobTable: {
            partitionKey: {
                name: 'InferenceJobId',
                type: AttributeType.STRING,
            },
        },
        SDEndpointDeploymentJobTable: {
            partitionKey: {
                name: 'EndpointDeploymentJobId',
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
    };

    for (let tableName in tables) {
        const val = tables[tableName];

        try {
            const KeySchema: KeySchemaElement[] = [
                {AttributeName: val.partitionKey.name, KeyType: 'HASH'},
            ];

            const AttributeDefinitions: AttributeDefinition[] = [
                {AttributeName: val.partitionKey.name, AttributeType: val.partitionKey.type},
            ];

            if (val.sortKey) {
                KeySchema.push({AttributeName: val.sortKey.name, KeyType: 'RANGE'});
                AttributeDefinitions.push({AttributeName: val.sortKey.name, AttributeType: val.sortKey.type});
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

async function createBucket(event: any) {
    const {bucketName} = event.ResourceProperties;
    try {
        const createBucketCommand = new CreateBucketCommand({
            Bucket: bucketName,
            ACL: 'private',
        });
        await s3Client.send(createBucketCommand);
    } catch (err: any) {
        if (err.Code === 'BucketAlreadyOwnedByYou') {
            console.log(`Bucket ${bucketName} exists.`);
        }
        if (err.Code === 'BucketAlreadyExists') {
            console.log(`Bucket ${bucketName} exists.`);
            throw new Error(`Bucket ${bucketName} exists. ${err.message}`);
        }
    }

    try {
        const headBucketCommand = new HeadBucketCommand({Bucket: bucketName});
        await s3Client.send(headBucketCommand);
    } catch (err: any) {
        console.log(err);
        throw new Error(`bucket ${bucketName} permission check failed.`);
    }

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

        const createTopicCommand = new CreateTopicCommand({
            Name,
        });
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
        const command: ListAliasesCommand = new ListAliasesCommand({Marker: nextToken});
        const response = await kmsClient.send(command);
        const alias = response.Aliases?.find(
            a => a.AliasName === aliasName,
        );
        if (alias) {
            return alias.TargetKeyId;
        }
        nextToken = response.NextMarker;
    } while (nextToken);

    return null;
}


async function createRole() {
    const name = 'LambdaStartDeployRole';

    try {

        // list policies from role
        const listRolePoliciesCommand = new ListRolePoliciesCommand({
            RoleName: name,
        });
        const listPolicies = await iamClient.send(listRolePoliciesCommand);

        if (!listPolicies['PolicyNames']) {
            return;
        }

        if (listPolicies['PolicyNames'].includes('LambdaStartDeployPolicy')) {
            return;
        }

        // put policy to the role
        const putRolePolicyCommand = new PutRolePolicyCommand({
            RoleName: name,
            PolicyName: 'LambdaStartDeployPolicy',
            PolicyDocument: JSON.stringify({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "sns:Publish",
                            "sns:ListSubscriptionsByTopic",
                            "sns:ListTopics"
                        ],
                        "Resource": [
                            "arn:aws:sns:*:*:StableDiffusionSnsUserTopic",
                            "arn:aws:sns:*:*:ReceiveSageMakerInferenceSuccess",
                            "arn:aws:sns:*:*:ReceiveSageMakerInferenceError"
                        ],
                        "Effect": "Allow"
                    },
                    {
                        "Action": [
                            "s3:Get*",
                            "s3:List*",
                            "s3:PutObject",
                            "s3:GetObject"
                        ],
                        "Resource": [
                            "arn:aws:s3:::*",
                            "arn:aws:s3:::*/*",
                        ],
                        "Effect": "Allow"
                    },
                    {
                        "Action": [
                            "sagemaker:DeleteModel",
                            "sagemaker:DeleteEndpoint",
                            "sagemaker:DescribeEndpoint",
                            "sagemaker:DeleteEndpointConfig",
                            "sagemaker:DescribeEndpointConfig",
                            "sagemaker:InvokeEndpoint",
                            "sagemaker:CreateModel",
                            "sagemaker:CreateEndpoint",
                            "sagemaker:CreateEndpointConfig",
                            "sagemaker:InvokeEndpointAsync",
                            "ecr:GetAuthorizationToken",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:GetRepositoryPolicy",
                            "ecr:DescribeRepositories",
                            "ecr:ListImages",
                            "ecr:DescribeImages",
                            "ecr:BatchGetImage",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload",
                            "ecr:PutImage",
                            "cloudwatch:PutMetricAlarm",
                            "cloudwatch:PutMetricData",
                            "cloudwatch:DeleteAlarms",
                            "cloudwatch:DescribeAlarms",
                            "sagemaker:UpdateEndpointWeightsAndCapacities",
                            "iam:CreateServiceLinkedRole",
                            "iam:PassRole",
                            "sts:AssumeRole"
                        ],
                        "Resource": "*",
                        "Effect": "Allow"
                    },
                    {
                        "Action": [
                            "dynamodb:Query",
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Describe*",
                            "dynamodb:List*",
                            "dynamodb:Scan"
                        ],
                        "Resource": [
                            "arn:aws:dynamodb:*:*:table/SDEndpointDeploymentJobTable",
                            "arn:aws:dynamodb:*:*:table/MultiUserTable",
                            "arn:aws:dynamodb:*:*:table/SDInferenceJobTable"
                        ],
                        "Effect": "Allow"
                    },
                    {
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": "arn:aws:logs:*:*:log-group:*:*",
                        "Effect": "Allow"
                    },
                    {
                        "Action": "iam:PassRole",
                        "Resource": "arn:aws:iam::*:role/ESDRoleForEndpoint-*",
                        "Effect": "Allow"
                    }
                ]
            }),
        });
        await iamClient.send(putRolePolicyCommand);


    } catch (err: any) {
        // it's ok if the role not exists
        if (err?.Error?.Message === `The role with name ${name} cannot be found.`) {
            return;
        }
        console.log(err?.Error?.Code);
        console.log(err?.Error?.Message);
        if (err?.Error?.Code !== 'NoSuchEntity') {
            throw err;
        }
    }

}
