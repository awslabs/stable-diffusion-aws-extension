import {PythonFunction, PythonFunctionProps} from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, Duration} from 'aws-cdk-lib'
import {MethodOptions} from 'aws-cdk-lib/aws-apigateway/lib/method';
import {Effect, PolicyStatement, Role, CompositePrincipal, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {Table} from "aws-cdk-lib/aws-dynamodb";
import {Bucket} from "aws-cdk-lib/aws-s3";
import {Topic} from 'aws-cdk-lib/aws-sns';
import {
    JsonSchemaType,
    JsonSchemaVersion,
    LambdaIntegration,
    Model,
    Resource,
    IAuthorizer,
    RequestValidator
} from "aws-cdk-lib/aws-apigateway";


export interface CreateSagemakerEndpointsApiProps {
    router: Resource;
    httpMethod: string;
    endpointDeploymentTable: Table;
    multiUserTable: Table;
    inferenceJobTable: Table;
    srcRoot: string;
    inferenceECRUrl: string;
    commonLayer: LayerVersion;
    authorizer: IAuthorizer;
    s3Bucket: Bucket;
    userNotifySNS: Topic;
    inferenceResultTopic: Topic;
    inferenceResultErrorTopic: Topic;
}

export class CreateSagemakerEndpointsApi {
    private readonly src;
    private readonly router: Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly endpointDeploymentTable: Table;
    private readonly multiUserTable: Table;
    private readonly inferenceJobTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;
    private readonly inferenceECRUrl: string;
    private readonly authorizer: IAuthorizer;
    private readonly s3Bucket: Bucket;
    private readonly userNotifySNS: Topic;
    private readonly inferenceResultTopic: Topic;
    private readonly inferenceResultErrorTopic: Topic;

    constructor(scope: Construct, id: string, props: CreateSagemakerEndpointsApiProps) {
        this.scope = scope;
        this.baseId = id;
        this.router = props.router;
        this.httpMethod = props.httpMethod;
        this.endpointDeploymentTable = props.endpointDeploymentTable;
        this.inferenceJobTable = props.inferenceJobTable;
        this.multiUserTable = props.multiUserTable;
        this.authorizer = props.authorizer;
        this.src = props.srcRoot;
        this.layer = props.commonLayer;
        this.s3Bucket = props.s3Bucket;
        this.inferenceECRUrl = props.inferenceECRUrl;
        this.userNotifySNS = props.userNotifySNS;
        this.inferenceResultTopic = props.inferenceResultTopic;
        this.inferenceResultErrorTopic = props.inferenceResultErrorTopic;

        console.log(this.userNotifySNS);

        this.createEndpointsApi();
    }

    private iamRole(): Role {

        const snsStatement = new PolicyStatement({
            actions: [
                'sns:Publish',
                'sns:ListSubscriptionsByTopic',
                'sns:ListTopics',
            ],
            resources: [
                this.userNotifySNS.topicArn,
                this.inferenceResultTopic.topicArn,
                this.inferenceResultErrorTopic.topicArn
            ],
        });

        const s3Statement = new PolicyStatement({
            actions: [
                's3:Get*',
                's3:List*',
                's3:PutObject',
                's3:GetObject',
            ],
            resources: [
                this.s3Bucket.bucketArn,
                `${this.s3Bucket.bucketArn}/*`,
                'arn:aws:s3:::*sagemaker*',
            ],
        });

        const endpointStatement = new PolicyStatement({
            actions: [
                'sagemaker:InvokeEndpoint',
                'sagemaker:CreateModel',
                'sagemaker:CreateEndpoint',
                'sagemaker:CreateEndpointConfig',
                'sagemaker:DescribeEndpoint',
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
                'sagemaker:DescribeEndpointConfig',
                'cloudwatch:DeleteAlarms',
                'cloudwatch:DescribeAlarms',
                'sagemaker:UpdateEndpointWeightsAndCapacities',
                'iam:CreateServiceLinkedRole',
                'iam:PassRole',
                'sts:AssumeRole',
            ],
            resources: ['*'],
        });

        const ddbStatement = new PolicyStatement({
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
                this.multiUserTable.tableArn,
                this.inferenceJobTable.tableArn,
            ],
        });

        const newRole = new Role(this.scope, `${this.baseId}-role`, {
            assumedBy: new CompositePrincipal(
                new ServicePrincipal('sagemaker.amazonaws.com'),
                new ServicePrincipal('lambda.amazonaws.com'),
            ),
        });

        const logStatement = new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
        });

        const passStartDeployRole = new PolicyStatement({
            actions: [
                'iam:PassRole',
            ],
            resources: [`arn:${Aws.PARTITION}:iam::${Aws.ACCOUNT_ID}:role/LambdaStartDeployRole`],
        });

        newRole.addToPolicy(snsStatement);
        newRole.addToPolicy(s3Statement);
        newRole.addToPolicy(endpointStatement);
        newRole.addToPolicy(ddbStatement);
        newRole.addToPolicy(logStatement);
        newRole.addToPolicy(passStartDeployRole);

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
            contentType: 'application/json',
            modelName: 'CreateEndpointModel',
            description: 'Create Endpoint Model',
            schema: {
                schema: JsonSchemaVersion.DRAFT4,
                title: "createEndpointSchema",
                type: JsonSchemaType.OBJECT,
                properties: {
                    "instance_type": {
                        type: JsonSchemaType.STRING,
                    },
                    "initial_instance_count": {
                        type: JsonSchemaType.NUMBER,
                    },
                    "autoscaling_enabled": {
                        type: JsonSchemaType.STRING,
                    },
                    "assign_to_roles": {
                        type: JsonSchemaType.ARRAY,
                        items: {
                            type: JsonSchemaType.STRING
                        },
                        minItems: 1,
                        maxItems: 10,
                    }
                },
                required: [
                    "instance_type",
                    "initial_instance_count",
                    "autoscaling_enabled",
                    "assign_to_roles",
                ]
            }
        });

        const integration = new LambdaIntegration(
            lambdaFunction,
            {
                proxy: false,
                integrationResponses: [{statusCode: '200'}],
            },
        );

        const requestValidator = new RequestValidator(this.scope, 'CreateEndpointRequestValidator', {
            restApi: this.router.api,
            requestValidatorName: 'CreateEndpointRequestValidator',
            validateRequestBody: true,
            validateRequestParameters: false,
        });

        this.router.addMethod(this.httpMethod, integration, <MethodOptions>{
            apiKeyRequired: true,
            authorizer: this.authorizer,
            requestValidator,
            requestModels: {
                'application/json': model,
            },
            methodResponses: [
                {
                    statusCode: '200',
                }, {statusCode: '500'}],
        });

    }
}
