import {PythonFunction, PythonFunctionProps} from '@aws-cdk/aws-lambda-python-alpha';
import {aws_iam, Duration} from 'aws-cdk-lib'
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {Table} from "aws-cdk-lib/aws-dynamodb";
import {Rule} from "aws-cdk-lib/aws-events";
import {LambdaFunction} from "aws-cdk-lib/aws-events-targets";

export interface SagemakerEndpointEventsProps {
    endpointDeploymentTable: Table;
    multiUserTable: Table;
    srcRoot: string;
    commonLayer: LayerVersion;
}

export class SagemakerEndpointEvents {
    private readonly src;
    private readonly scope: Construct;
    private readonly endpointDeploymentTable: Table;
    private readonly multiUserTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;


    constructor(scope: Construct, id: string, props: SagemakerEndpointEventsProps) {
        this.scope = scope;
        this.baseId = id;
        this.endpointDeploymentTable = props.endpointDeploymentTable;
        this.multiUserTable = props.multiUserTable;
        this.src = props.srcRoot;
        this.layer = props.commonLayer;

        this.createEndpointEventBridge();
    }

    private iamRole(): Role {

        const newRole = new Role(this.scope, `${this.baseId}-eb-role`, {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });

        newRole.addToPolicy(new aws_iam.PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'dynamodb:UpdateItem',
                'dynamodb:Scan',
                'dynamodb:GetItem',
            ],
            resources: [
                this.endpointDeploymentTable.tableArn,
                this.multiUserTable.tableArn,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'sagemaker:DeleteEndpoint',
                'sagemaker:DescribeEndpoint',
                'sagemaker:DescribeEndpointConfig',
                'sagemaker:UpdateEndpointWeightsAndCapacities',
                'cloudwatch:DeleteAlarms',
                'cloudwatch:DescribeAlarms',
                'cloudwatch:PutMetricAlarm',
                'application-autoscaling:PutScalingPolicy',
                'application-autoscaling:RegisterScalableTarget',
            ],
            resources: [`*`],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
            ],
            resources: ['*'],
        }));

        return newRole;
    }

    private createEndpointEventBridge() {

        const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-delete-endpoints`, <PythonFunctionProps>{
            functionName: `${this.baseId}-function`,
            entry: `${this.src}/inference_v2`,
            architecture: Architecture.X86_64,
            runtime: Runtime.PYTHON_3_9,
            index: 'sagemaker_endpoint_api.py',
            handler: 'sagemaker_endpoint_events',
            timeout: Duration.seconds(900),
            role: this.iamRole(),
            memorySize: 1024,
            environment: {
                DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
                MULTI_USER_TABLE: this.multiUserTable.tableName,
            },
            layers: [this.layer],
        });

        const rule = new Rule(this.scope, 'SageMakerEndpointStateChangeRule', {
            eventPattern: {
                source: ['aws.sagemaker'],
                detailType: ['SageMaker Endpoint State Change'],
                detail: {
                    EndpointName: [
                        {
                            prefix: 'infer-endpoint-'
                        }
                    ]
                }
            },
        });

        rule.addTarget(new LambdaFunction(lambdaFunction));

    }
}
