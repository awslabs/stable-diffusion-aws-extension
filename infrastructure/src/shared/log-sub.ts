import { Aws, Duration } from 'aws-cdk-lib';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { Construct } from 'constructs';
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';

export class LogSub extends Construct {
    public readonly lambda: NodejsFunction;

    constructor(scope: Construct, id: string) {
        super(scope, id);

        const role = this.iamRole()

        this.lambda = new NodejsFunction(scope, 'LogSubHandler', {
            runtime: Runtime.NODEJS_18_X,
            handler: 'handler',
            entry: 'src/shared/log-sub-on-event.ts',
            bundling: {
                minify: true,
                externalModules: ['aws-cdk-lib'],
            },
            timeout: Duration.seconds(900),
            role: role,
            memorySize: 3070,
        });

        this.lambda.addPermission('AllowCloudWatchLogsToInvoke', {
            principal: new ServicePrincipal('logs.amazonaws.com'),
            action: 'lambda:InvokeFunction',
            sourceArn: `arn:aws:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:/aws/sagemaker/Endpoints/*:*`,
        });

    }

    private iamRole(): Role {

        const newRole = new Role(this, 'log-sub-lambda-role', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                's3:ListBucket',
                's3:GetObject',
                's3:PutObject',
                's3:HeadObject',
                's3:DeleteObject',
            ],
            resources: [
                `arn:${Aws.PARTITION}:s3:::*`,
            ],
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

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'iam:PassRole',
            ],
            resources: [
                `arn:${Aws.PARTITION}:iam::${Aws.ACCOUNT_ID}:role/*`,
            ],
        }));

        return newRole;
    }

}
