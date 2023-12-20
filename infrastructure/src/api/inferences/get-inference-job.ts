import {PythonFunction} from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, Duration} from 'aws-cdk-lib';
import {LambdaIntegration, Resource,} from 'aws-cdk-lib/aws-apigateway';
import {Table} from 'aws-cdk-lib/aws-dynamodb';
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {Bucket} from "aws-cdk-lib/aws-s3";

export interface GetInferenceJobApiProps {
    router: Resource;
    httpMethod: string;
    inferenceJobTable: Table;
    srcRoot: string;
    commonLayer: LayerVersion;
    s3Bucket: Bucket;
}

export class GetInferenceJobApi {
    private readonly src: string;
    private readonly router: Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly inferenceJobTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;
    private readonly s3Bucket: Bucket;

    constructor(scope: Construct, id: string, props: GetInferenceJobApiProps) {
        this.scope = scope;
        this.baseId = id;
        this.router = props.router;
        this.httpMethod = props.httpMethod;
        this.inferenceJobTable = props.inferenceJobTable;
        this.src = props.srcRoot;
        this.layer = props.commonLayer;
        this.s3Bucket = props.s3Bucket;

        this.getInferenceJobsApi();
    }

    private getInferenceJobsApi() {

        const lambdaFunction = new PythonFunction(
            this.scope,
            `${this.baseId}-lambda`,
            {
                entry: `${this.src}/inferences`,
                architecture: Architecture.X86_64,
                runtime: Runtime.PYTHON_3_9,
                index: 'get_inference_job.py',
                handler: 'handler',
                timeout: Duration.seconds(900),
                role: this.iamRole(),
                memorySize: 1024,
                environment: {
                    INFERENCE_JOB_TABLE: this.inferenceJobTable.tableName,
                    S3_BUCKET_NAME: this.s3Bucket.bucketName,
                },
                layers: [this.layer],
            });


        const lambdaIntegration = new LambdaIntegration(
            lambdaFunction,
            {
                proxy: true
            },
        );


        this.router.addMethod(
            this.httpMethod,
            lambdaIntegration,
            {
                apiKeyRequired: true,
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
                // get an inference job
                'dynamodb:GetItem',
            ],
            resources: [
                this.inferenceJobTable.tableArn,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            actions: [
                's3:GetObject',
            ],
            resources: [
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
