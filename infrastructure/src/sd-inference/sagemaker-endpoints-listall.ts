import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  Duration,
} from 'aws-cdk-lib';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';


export interface ListAllSageMakerEndpointsApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  endpointDeploymentTable: aws_dynamodb.Table;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  authorizer: aws_apigateway.IAuthorizer;
}

export class ListAllSagemakerEndpointsApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly endpointDeploymentTable: aws_dynamodb.Table;
  private readonly multiUserTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly baseId: string;
  private readonly authorizer: aws_apigateway.IAuthorizer;


  constructor(scope: Construct, id: string, props: ListAllSageMakerEndpointsApiProps) {
    this.scope = scope;
    this.baseId = id;
    this.router = props.router;
    this.httpMethod = props.httpMethod;
    this.endpointDeploymentTable = props.endpointDeploymentTable;
    this.multiUserTable = props.multiUserTable;
    this.authorizer = props.authorizer;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;

    this.listAllSageMakerEndpointsApi();
  }

  private iamRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
      ],
      resources: [
        this.endpointDeploymentTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
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

  private listAllSageMakerEndpointsApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/inference_v2`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'sagemaker_endpoint_api.py',
      handler: 'list_all_sagemaker_endpoints',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DDB_ENDPOINT_DEPLOYMENT_TABLE_NAME: this.endpointDeploymentTable.tableName,
        MULTI_USER_TABLE: this.multiUserTable.tableName,
      },
      layers: [this.layer],
    });

    const listSagemakerEndpointsIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );
    this.router.addMethod(this.httpMethod, listSagemakerEndpointsIntegration, <MethodOptions>{
      apiKeyRequired: true,
      authorizer: this.authorizer,
    });
  }
}

