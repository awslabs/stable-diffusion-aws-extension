import { Aws, Duration } from 'aws-cdk-lib';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { NodejsFunction } from 'aws-cdk-lib/aws-lambda-nodejs';
import { Construct } from 'constructs';
import { Effect, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';

export class LogSub extends Construct {
    public readonly lambda: NodejsFunction;

    constructor(scope: Construct, id: string) {
        super(scope, id);

        this.lambda = new NodejsFunction(scope, 'LogSubHandler', {
            runtime: Runtime.NODEJS_18_X,
            handler: 'handler',
            entry: 'src/shared/log-sub-on-event.ts',
            bundling: {
                minify: true,
                externalModules: ['aws-cdk-lib'],
            },
            timeout: Duration.seconds(900),
            role: this.iamRole(),
            memorySize: 3070,
        });

    }

    private iamRole(): Role {

        const newRole = new Role(this, 'log-sub-role', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                's3:ListBucket',
                's3:CreateBucket',
                's3:PutBucketCORS',
                's3:GetObject',
                's3:PutObject',
                's3:HeadObject',
                's3:DeleteObject',
                's3:GetBucketLocation',
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
