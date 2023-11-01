import {PythonFunction, PythonFunctionProps} from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_sns as sns, Duration} from 'aws-cdk-lib'
import {MethodOptions} from 'aws-cdk-lib/aws-apigateway/lib/method';
import {Effect, PolicyStatement, Role} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {Table} from "aws-cdk-lib/aws-dynamodb";
import {
    JsonSchemaType,
    JsonSchemaVersion,
    LambdaIntegration,
    Model,
    Resource,
    IAuthorizer
} from "aws-cdk-lib/aws-apigateway";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";


export interface CreateSagemakerEndpointsApiProps {
    router: Resource;
    httpMethod: string;
    endpointDeploymentTable: Table;
    multiUserTable: Table;
    srcRoot: string;
    inferenceECRUrl: string;
    commonLayer: LayerVersion;
    authorizer: IAuthorizer;
    s3Bucket: s3.Bucket;
    userNotifySNS: sns.Topic;
    inferenceResultTopic: sns.Topic;
    inferenceResultErrorTopic: sns.Topic;
}

export class CreateSagemakerEndpointsApi {
    private readonly src;
    private readonly router: Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly endpointDeploymentTable: Table;
    private readonly multiUserTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;
    private readonly inferenceECRUrl: string;
    private readonly authorizer: IAuthorizer;
    private readonly s3Bucket: s3.Bucket;
    private readonly userNotifySNS: sns.Topic;
    private readonly inferenceResultTopic: sns.Topic;
    private readonly inferenceResultErrorTopic: sns.Topic;

    constructor(scope: Construct, id: string, props: CreateSagemakerEndpointsApiProps) {
        this.scope = scope;
        this.baseId = id;
        this.router = props.router;
        this.httpMethod = props.httpMethod;
        this.endpointDeploymentTable = props.endpointDeploymentTable;
        this.multiUserTable = props.multiUserTable;
        this.authorizer = props.authorizer;
        this.src = props.srcRoot;
        this.layer = props.commonLayer;
        this.s3Bucket = props.s3Bucket;
        this.userNotifySNS = props.userNotifySNS;
        this.inferenceECRUrl = props.inferenceECRUrl;
        this.inferenceResultTopic = props.inferenceResultTopic;
        this.inferenceResultErrorTopic = props.inferenceResultErrorTopic;

        console.log(this.userNotifySNS);

        this.createEndpointsApi();
    }

    private iamRole(): Role {

        const newRole = new Role(this.scope, `${this.baseId}-role`, {
            assumedBy: new iam.CompositePrincipal(
                new iam.ServicePrincipal('sagemaker.amazonaws.com'),
                new iam.ServicePrincipal('lambda.amazonaws.com'),
            ),
        });

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'iam:PassRole',
                'iam:CreateServiceLinkedRole',
                'sts:AssumeRole',
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
                'sagemaker:CreateModel',
                'sagemaker:InvokeEndpoint',
                'sagemaker:CreateEndpoint',
                'sagemaker:DescribeEndpoint',
                'sagemaker:InvokeEndpointAsync',
                'sagemaker:CreateEndpointConfig',
                'sagemaker:DescribeEndpointConfig',
                'sagemaker:UpdateEndpointWeightsAndCapacities',
                'cloudwatch:PutMetricAlarm',
                'cloudwatch:PutMetricData',
                'cloudwatch:DeleteAlarms',
                'cloudwatch:DescribeAlarms',
            ],
            resources: [
                `*`,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                's3:Get*',
                's3:List*',
                's3:PutObject',
                's3:GetObject',
            ],
            resources: [
                this.s3Bucket.bucketArn,
                `${this.s3Bucket.bucketArn}/*`,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'sns:Publish',
                'sns:ListTopics',
            ],
            resources: [
                this.userNotifySNS.topicArn,
                this.inferenceResultErrorTopic.topicArn,
                this.inferenceResultTopic.topicArn,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'dynamodb:Query',
                'dynamodb:GetItem',
                'dynamodb:PutItem',
                'dynamodb:DeleteItem',
                'dynamodb:UpdateItem',
                'dynamodb:Describe*',
                'dynamodb:List*',
                'dynamodb:Scan',
            ],
            resources: [
                this.endpointDeploymentTable.tableArn,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
        }));

        return newRole;
    }

    private createEndpointsApi() {

        const role = this.iamRole();

        const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
            functionName: `${this.baseId}-api`,
            entry: `${this.src}/inference_v2`,
            architecture: Architecture.X86_64,
            runtime: Runtime.PYTHON_3_9,
            index: 'sagemaker_endpoint_api.py',
            handler: 'sagemaker_endpoint_create_api',
            timeout: Duration.seconds(900),
            role: role,
            memorySize: 1024,
            environment: {
                DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
                MULTI_USER_TABLE: this.multiUserTable.tableName,
                S3_BUCKET_NAME: this.s3Bucket.bucketName,
                INFERENCE_ECR_IMAGE_URL: this.inferenceECRUrl,
                SNS_INFERENCE_SUCCESS: this.inferenceResultTopic.topicArn,
                SNS_INFERENCE_ERROR: this.inferenceResultErrorTopic.topicArn,
                EXECUTION_ROLE_ARN: role.roleArn,
            },
            layers: [this.layer],
        });

        const model = new Model(this.scope, 'CreateEndpointModel', {
            restApi: this.router.api,
            modelName: 'CreateEndpointModel',
            description: 'Create Endpoint Model',
            schema: {
                schema: JsonSchemaVersion.DRAFT4,
                title: "createEndpointSchema",
                type: JsonSchemaType.OBJECT,
                properties: {
                    "delete_endpoint_list": {
                        type: JsonSchemaType.ARRAY,
                        items: {
                            type: JsonSchemaType.STRING
                        },
                        minItems: 1,
                        maxItems: 10,
                    }
                },
                required: ["delete_endpoint_list"]
            },
            contentType: 'application/json'
        });

        console.log(model.modelId);

        const integration = new LambdaIntegration(
            lambdaFunction,
            {
                proxy: false,
                integrationResponses: [{statusCode: '200'}],
            },
        );

        this.router.addMethod(this.httpMethod, integration, <MethodOptions>{
            apiKeyRequired: true,
            authorizer: this.authorizer,
            // requestValidatorOptions: {
            //     // requestValidatorName: "create-endpoint-validator",
            //     validateRequestBody: true,
            // },
            // requestModels: {
            //     'application/json': model,
            // },
            methodResponses: [
                {
                    statusCode: '200',
                }, {statusCode: '500'}],
        });

    }
}
