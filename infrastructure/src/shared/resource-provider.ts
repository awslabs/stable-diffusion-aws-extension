import {CustomResource, Duration, SecretValue} from 'aws-cdk-lib';
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Runtime} from 'aws-cdk-lib/aws-lambda';
import {NodejsFunction} from 'aws-cdk-lib/aws-lambda-nodejs';
import {RetentionDays} from 'aws-cdk-lib/aws-logs';
import {Provider} from 'aws-cdk-lib/custom-resources';
import {Construct} from 'constructs';


export class ResourceProvider extends Construct {

    public readonly resources: CustomResource;

    constructor(scope: Construct, id: string, bucketName: string) {
        super(scope, id);
        const role = this.iamRole();

        const onEventHandler = new NodejsFunction(scope, 'onEventHandler', {
            runtime: Runtime.NODEJS_18_X,
            handler: 'handler',
            entry: 'src/shared/resource-provider-on-event.ts',
            bundling: {
                minify: true,
                externalModules: ['aws-cdk-lib'],
            },
            timeout: Duration.seconds(900),
            role,
            memorySize: 4048,
        });

        const provider = new Provider(scope, 'ResourceProvider', {
            onEventHandler: onEventHandler,
            logRetention: RetentionDays.ONE_DAY,
        });

        // use random string to trigger the custom resource every time
        const randomString = SecretValue.secretsManager('random-string-id', {
            jsonField: 'random',
        }).toString();

        this.resources = new CustomResource(scope, 'CustomResource', {
            serviceToken: provider.serviceToken,
            properties: {bucketName, randomString},
        });

    }

    private iamRole(): Role {

        const newRole = new Role(this, 'deploy-check-role', {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'dynamodb:CreateTable',
                'sns:CreateTopic',
                "iam:ListRolePolicies",
                "iam:PutRolePolicy",
                'kms:CreateKey',
                'kms:CreateAlias',
                'kms:DisableKeyRotation',
                'kms:ListAliases',
            ],
            resources: [
                '*',
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                's3:ListBucket',
                's3:CreateBucket',
            ],
            resources: [
                'arn:aws:s3:::*',
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'kms:Decrypt',
            ],
            resources: ['*'],
        }));
        return newRole;
    }

}
