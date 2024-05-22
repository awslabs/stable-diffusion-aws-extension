import {PythonFunction} from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_lambda, Duration} from 'aws-cdk-lib';
import {JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource} from 'aws-cdk-lib/aws-apigateway';
import {Table} from 'aws-cdk-lib/aws-dynamodb';
import {Effect, PolicyStatement, Role, ServicePrincipal} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {ApiModels} from '../../shared/models';
import {SCHEMA_WORKFLOW_NAME} from '../../shared/schema';
import {ApiValidators} from '../../shared/validator';

export interface DeleteWorkflowsApiProps {
    router: Resource;
    httpMethod: string;
    workflowsTable: Table;
    multiUserTable: Table;
    commonLayer: LayerVersion;
}

export class DeleteWorkflowsApi {
    private readonly router: Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly workflowsTable: Table;
    private readonly multiUserTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;

    constructor(scope: Construct, id: string, props: DeleteWorkflowsApiProps) {
        this.scope = scope;
        this.baseId = id;
        this.router = props.router;
        this.httpMethod = props.httpMethod;
        this.workflowsTable = props.workflowsTable;
        this.multiUserTable = props.multiUserTable;
        this.layer = props.commonLayer;

        const lambdaFunction = this.apiLambda();

        const lambdaIntegration = new LambdaIntegration(
            lambdaFunction,
            {
                proxy: true,
            },
        );

        this.router.addMethod(this.httpMethod, lambdaIntegration, {
            apiKeyRequired: true,
            requestValidator: ApiValidators.bodyValidator,
            requestModels: {
                'application/json': this.createRequestBodyModel(),
            },
            operationName: 'DeleteWorkflows',
            methodResponses: [
                ApiModels.methodResponses204(),
                ApiModels.methodResponses400(),
                ApiModels.methodResponses401(),
                ApiModels.methodResponses403(),
            ],
        });
    }

    private iamRole(): Role {

        const newRole = new Role(this.scope, `${this.baseId}-role`, {
            assumedBy: new ServicePrincipal('lambda.amazonaws.com'),
        });


        newRole.addToPolicy(new PolicyStatement({
            actions: [
                'dynamodb:Query',
                'dynamodb:GetItem',
                'dynamodb:PutItem',
                'dynamodb:DeleteItem',
                'dynamodb:UpdateItem',
                'dynamodb:Describe*',
                'dynamodb:List*',
            ],
            resources: [
                this.workflowsTable.tableArn,
                `${this.workflowsTable.tableArn}/*`,
                this.multiUserTable.tableArn,
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            actions: [
                's3:Get*',
                's3:List*',
                's3:PutObject',
                's3:GetObject',
                's3:DeleteObject',
            ],
            resources: [
                '*',
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'cloudwatch:DeleteAlarms',
                'cloudwatch:DescribeAlarms',
                'cloudwatch:DeleteDashboards',
            ],
            resources: [
                '*',
            ],
        }));

        newRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'logs:DeleteLogGroup',
            ],
            resources: [`arn:${Aws.PARTITION}:logs:${Aws.REGION}:${Aws.ACCOUNT_ID}:log-group:*:*`],
        }));

        return newRole;
    }

    private createRequestBodyModel(): Model {
        return new Model(this.scope, `${this.baseId}-model`, {
            restApi: this.router.api,
            modelName: this.baseId,
            description: `Request Model ${this.baseId}`,
            schema: {
                schema: JsonSchemaVersion.DRAFT7,
                title: this.baseId,
                type: JsonSchemaType.OBJECT,
                properties: {
                    workflow_name_list: {
                        type: JsonSchemaType.ARRAY,
                        items: SCHEMA_WORKFLOW_NAME,
                        minItems: 1,
                        maxItems: 10,
                    },
                },
                required: [
                    'workflow_name_list',
                ],
            },
            contentType: 'application/json',
        });
    }

    private apiLambda() {
        return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
            entry: '../middleware_api/workflows',
            architecture: Architecture.X86_64,
            runtime: Runtime.PYTHON_3_10,
            index: 'delete_workflows.py',
            handler: 'handler',
            timeout: Duration.seconds(900),
            role: this.iamRole(),
            memorySize: 2048,
            tracing: aws_lambda.Tracing.ACTIVE,
            layers: [this.layer],
            environment:{
                WORKFLOWS_TABLE: this.workflowsTable.tableName,
            }
        });
    }


}
