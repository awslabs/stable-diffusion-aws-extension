import {PythonFunction} from '@aws-cdk/aws-lambda-python-alpha';
import {Aws, aws_lambda, Duration} from 'aws-cdk-lib';
import {JsonSchemaType, JsonSchemaVersion, LambdaIntegration, Model, Resource} from 'aws-cdk-lib/aws-apigateway';
import {Table} from 'aws-cdk-lib/aws-dynamodb';
import {Role} from 'aws-cdk-lib/aws-iam';
import {Architecture, LayerVersion, Runtime} from 'aws-cdk-lib/aws-lambda';
import {Construct} from 'constructs';
import {ApiModels} from '../../shared/models';
import {ApiValidators} from '../../shared/validator';
import {SCHEMA_WORKFLOW_JSON_NAME} from "../../shared/schema";
import {ESD_ROLE} from "../../shared/const";

export interface DeleteSchemasApiProps {
    router: Resource;
    httpMethod: string;
    workflowsSchemasTable: Table;
    commonLayer: LayerVersion;
}

export class DeleteSchemasApi {
    private readonly router: Resource;
    private readonly httpMethod: string;
    private readonly scope: Construct;
    private readonly workflowsSchemasTable: Table;
    private readonly layer: LayerVersion;
    private readonly baseId: string;

    constructor(scope: Construct, id: string, props: DeleteSchemasApiProps) {
        this.scope = scope;
        this.baseId = id;
        this.router = props.router;
        this.httpMethod = props.httpMethod;
        this.workflowsSchemasTable = props.workflowsSchemasTable;
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
            operationName: 'DeleteSchemas',
            methodResponses: [
                ApiModels.methodResponses204(),
                ApiModels.methodResponses400(),
                ApiModels.methodResponses401(),
                ApiModels.methodResponses403(),
            ],
        });
    }

    private createRequestBodyModel(): Model {
        return new Model(this.scope, `${this.baseId}-model`, {
            restApi: this.router.api,
            modelName: `${this.baseId}Request`,
            description: `Request Model ${this.baseId}`,
            schema: {
                schema: JsonSchemaVersion.DRAFT7,
                title: this.baseId,
                type: JsonSchemaType.OBJECT,
                properties: {
                    schema_name_list: {
                        type: JsonSchemaType.ARRAY,
                        items: SCHEMA_WORKFLOW_JSON_NAME,
                        minItems: 1,
                        maxItems: 10,
                    },
                },
                required: [
                    'schema_name_list',
                ],
            },
            contentType: 'application/json',
        });
    }

    private apiLambda() {
        const role = <Role>Role.fromRoleName(this.scope, `${this.baseId}-role`, `${ESD_ROLE}-${Aws.REGION}`);

        return new PythonFunction(this.scope, `${this.baseId}-lambda`, {
            entry: '../middleware_api/schemas',
            architecture: Architecture.X86_64,
            runtime: Runtime.PYTHON_3_10,
            index: 'delete_schemas.py',
            handler: 'handler',
            timeout: Duration.seconds(900),
            role: role,
            memorySize: 2048,
            tracing: aws_lambda.Tracing.ACTIVE,
            layers: [this.layer],
            environment:{
                WORKFLOW_SCHEMA_TABLE: this.workflowsSchemasTable.tableName,
            }
        });
    }


}
