import {PythonFunction} from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, Duration} from 'aws-cdk-lib';
import {
    JsonSchemaType,
    JsonSchemaVersion,
    LambdaIntegration,
    Model,
    RequestValidator,
    Resource,
} from 'aws-cdk-lib/aws-apigateway';
import {Table} from 'aws-cdk-lib/aws-dynamodb';
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {Bucket} from "aws-cdk-lib/aws-s3";

export interface DeleteDatasetsApiProps {
    router: Resource;
    httpMethod: string;
    datasetInfoTable: Table;
    datasetItemTable: Table;
    srcRoot: string;
    commonLayer: LayerVersion;
    s3Bucket: Bucket;
}

export class DeleteDatasetsApi {
    private readonly src: string;
    private readonly router: Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly datasetInfoTable: Table;
    private readonly datasetItemTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;
    private readonly s3Bucket: Bucket;

    constructor(scope: Construct, id: string, props: DeleteDatasetsApiProps) {
        this.scope = scope;
        this.baseId = id;
        this.router = props.router;
        this.httpMethod = props.httpMethod;
        this.datasetInfoTable = props.datasetInfoTable;
        this.datasetItemTable = props.datasetItemTable;
        this.src = props.srcRoot;
        this.layer = props.commonLayer;
        this.s3Bucket = props.s3Bucket;

        this.deleteDatasetsApi();
    }

    private deleteDatasetsApi() {

        const lambdaFunction = new PythonFunction(
            this.scope,
            `${this.baseId}-lambda`,
            {
                entry: `${this.src}/datasets`,
                architecture: Architecture.X86_64,
                runtime: Runtime.PYTHON_3_9,
                index: 'delete_datasets.py',
                handler: 'handler',
                timeout: Duration.seconds(900),
                role: this.iamRole(),
                memorySize: 1024,
                environment: {
                    DATASET_INFO_TABLE: this.datasetInfoTable.tableName,
                    DATASET_ITEM_TABLE: this.datasetItemTable.tableName,
                    S3_BUCKET_NAME: this.s3Bucket.bucketName,
                },
                layers: [this.layer],
            });

        const requestModel = new Model(
            this.scope,
            `${this.baseId}-model`,
            {
                restApi: this.router.api,
                modelName: this.baseId,
                description: `${this.baseId} Request Model`,
                schema: {
                    schema: JsonSchemaVersion.DRAFT4,
                    title: this.baseId,
                    type: JsonSchemaType.OBJECT,
                    properties: {
                        dataset_name_list: {
                            type: JsonSchemaType.ARRAY,
                            items: {
                                type: JsonSchemaType.STRING,
                                minLength: 1,
                            },
                            minItems: 1,
                            maxItems: 10,
                        },
                    },
                    required: [
                        'dataset_name_list',
                    ],
                },
                contentType: 'application/json',
            });

        const lambdaIntegration = new LambdaIntegration(
            lambdaFunction,
            {
                proxy: true
            },
        );

        const requestValidator = new RequestValidator(
            this.scope,
            `${this.baseId}-validator`,
            {
                restApi: this.router.api,
                requestValidatorName: this.baseId,
                validateRequestBody: true,
            });

        this.router.addMethod(
            this.httpMethod,
            lambdaIntegration,
            {
                apiKeyRequired: true,
                requestValidator,
                requestModels: {
                    'application/json': requestModel,
                }
            });

    }

    private iamRole(): Role {

        const newRole = new Role(
            this.scope,
            `${this.baseId}-role`,
            {
                assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
            }
        );

        newRole.addToPolicy(new PolicyStatement({
            actions: [
                // query dataset files
                'dynamodb:Query',
                // delete dataset
                'dynamodb:DeleteItem',
            ],
            resources: [
                this.datasetInfoTable.tableArn,
                this.datasetItemTable.tableArn,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            actions: [
                // list dataset items by prefix
                's3:ListBucket',
                // delete dataset file
                's3:DeleteObject',
            ],
            resources: [
                `${this.s3Bucket.bucketArn}`,
                `${this.s3Bucket.bucketArn}/*`,
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
}
