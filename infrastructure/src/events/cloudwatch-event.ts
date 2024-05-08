import {PythonFunction} from '@aws-cdk/aws-lambda-python-alpha';
import {aws_iam, aws_lambda, Duration} from 'aws-cdk-lib';
import {Table} from 'aws-cdk-lib/aws-dynamodb';
import {Rule} from 'aws-cdk-lib/aws-events';
import {LambdaFunction} from 'aws-cdk-lib/aws-events-targets';
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';

export interface EndpointsCloudwatchEventsProps {
    endpointDeploymentTable: Table;
    commonLayer: LayerVersion;
}

export class EndpointsCloudwatchEvents {
    private readonly scope: Construct;
    private readonly endpointDeploymentTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;

    constructor(scope: Construct, id: string, props: EndpointsCloudwatchEventsProps) {
        this.scope = scope;
        this.baseId = id;
        this.endpointDeploymentTable = props.endpointDeploymentTable;
        this.layer = props.commonLayer;

        this.createEventBridge();
    }

    private iamRole(): Role {

        const newRole = new Role(this.scope, `${this.baseId}-role`, {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });

        newRole.addToPolicy(new aws_iam.PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'dynamodb:Query',
                'dynamodb:GetItem',
            ],
            resources: [
                this.endpointDeploymentTable.tableArn,
                `${this.endpointDeploymentTable.tableArn}/*`,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'sagemaker:ListEndpoints',
                'cloudwatch:GetDashboard',
                'cloudwatch:PutDashboard',
                'cloudwatch:ListMetrics',
                's3:Get*',
                's3:List*',
                's3:DeleteObject',
            ],
            resources: ['*'],
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

    private createEventBridge() {

        const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, {
            entry: '../middleware_api/endpoints',
            architecture: Architecture.X86_64,
            runtime: Runtime.PYTHON_3_10,
            index: 'cloudwatch_event.py',
            handler: 'handler',
            timeout: Duration.seconds(900),
            role: this.iamRole(),
            memorySize: 3070,
            tracing: aws_lambda.Tracing.ACTIVE,
            layers: [this.layer],
        });

        const rule = new Rule(this.scope, `${this.baseId}-rule`, {
            eventPattern: {
                source: ['aws.cloudwatch'],
                detailType: ["AWS API Call via CloudTrail"],
                // detail: {
                //     "eventSource": ["cloudwatch.amazonaws.com"],
                //     "eventName": ["PutMetricData"],
                //     "requestParameters": {
                //         "dimensions": [{}, {"exists": false}]
                //     }
                // }
            },
        });

        rule.addTarget(new LambdaFunction(lambdaFunction));

    }
}
