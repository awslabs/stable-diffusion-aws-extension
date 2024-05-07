import {PythonFunction, PythonFunctionProps} from '@aws-cdk/aws-lambda-python-alpha';
import {aws_apigateway, aws_dynamodb, aws_iam, aws_lambda, Duration} from 'aws-cdk-lib';
import {JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model} from 'aws-cdk-lib/aws-apigateway';
import {Effect} from 'aws-cdk-lib/aws-iam';
import {Architecture, Runtime} from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import {Construct} from 'constructs';
import {ApiModels} from '../../shared/models';
import {SCHEMA_DEBUG, SCHEMA_MESSAGE,} from '../../shared/schema';


export interface GetExecuteLogsProps {
    httpMethod: string;
    router: aws_apigateway.Resource;
    s3Bucket: s3.Bucket;
    executeTable: aws_dynamodb.Table;
    commonLayer: aws_lambda.LayerVersion;
}


export class GetExecuteLogsApi {
    public lambdaIntegration: aws_apigateway.LambdaIntegration;
    private readonly baseId: string;
    private readonly router: aws_apigateway.Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly layer: aws_lambda.LayerVersion;
    private readonly s3Bucket: s3.Bucket;
    private readonly executeTable: aws_dynamodb.Table;

    constructor(scope: Construct, id: string, props: GetExecuteLogsProps) {
        this.scope = scope;
        this.httpMethod = props.httpMethod;
        this.baseId = id;
        this.router = props.router;
        this.s3Bucket = props.s3Bucket;
        this.executeTable = props.executeTable;
        this.layer = props.commonLayer;

        const lambdaFunction = this.apiLambda();

        this.lambdaIntegration = new LambdaIntegration(
            lambdaFunction,
            {
                proxy: true,
            },
        );

        this.router.addResource('logs')
            .addMethod(this.httpMethod, this.lambdaIntegration, {
                apiKeyRequired: true,
                operationName: 'GetExecuteLogs',
                methodResponses: [
                    ApiModels.methodResponse(this.responseModel()),
                    ApiModels.methodResponses401(),
                    ApiModels.methodResponses403(),
                    ApiModels.methodResponses404(),
                ],
            });
    }

    private responseModel() {
        return new Model(this.scope, `${this.baseId}-logs-resp-model`, {
            restApi: this.router.api,
            modelName: 'GetExecuteLogsResponse',
            description: `Response Model ${this.baseId}`,
            schema: {
                schema: JsonSchemaVersion.DRAFT7,
                type: JsonSchemaType.OBJECT,
                title: 'GetExecuteLogsResponse',
                properties: {
                    statusCode: {
                        type: JsonSchemaType.INTEGER,
                        enum: [
                            200,
                        ],
                    },
                    debug: SCHEMA_DEBUG,
                    message: SCHEMA_MESSAGE,
                    data: {
                        type: JsonSchemaType.OBJECT,
                        properties: {
                            message_type: {
                                type: JsonSchemaType.STRING,
                            },
                            message: {
                                type: JsonSchemaType.STRING,
                            },
                            logGroup: {
                                type: JsonSchemaType.STRING,
                            },
                            id: {
                                type: JsonSchemaType.STRING,
                            },
                            logStream: {
                                type: JsonSchemaType.STRING,
                            },
                            timestamp: {
                                type: JsonSchemaType.STRING,
                            },
                        },
                        required: [
                            'message_type',
                            'message',
                            'logGroup',
                            'id',
                            'logStream',
                            'timestamp',
                        ],
                    },
                },
                required: [
                    'statusCode',
                    'debug',
                    'data',
                    'message',
                ],
            }
            ,
            contentType: 'application/json',
        });
    }

    private apiLambda() {
        return new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
            entry: '../middleware_api/comfy',
            architecture: Architecture.X86_64,
            runtime: Runtime.PYTHON_3_10,
            index: 'get_execute_logs.py',
            handler: 'handler',
            timeout: Duration.seconds(900),
            role: this.iamRole(),
            memorySize: 2048,
            tracing: aws_lambda.Tracing.ACTIVE,
            environment: {
                EXECUTE_TABLE: this.executeTable.tableName,
            },
            layers: [this.layer],
        });
    }

    private iamRole(): aws_iam.Role {
        const newRole = new aws_iam.Role(this.scope, `${this.baseId}-role`, {
            assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
        });

        newRole.addToPolicy(new aws_iam.PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'dynamodb:GetItem',
            ],
            resources: [
                this.executeTable.tableArn,
                `${this.executeTable.tableArn}/*`,
            ],
        }));

        newRole.addToPolicy(new aws_iam.PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                's3:GetObject',
                's3:PutObject',
                's3:DeleteObject',
                's3:ListBucket',
            ],
            resources: [
                `${this.s3Bucket.bucketArn}/*`,
                `${this.s3Bucket.bucketArn}`,
            ],
        }));

        newRole.addToPolicy(new aws_iam.PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                "logs:StartQuery",
                "logs:GetQueryResults",
                "logs:DescribeLogGroups"
            ],
            resources: ['*'],
        }));

        return newRole;
    }

}

