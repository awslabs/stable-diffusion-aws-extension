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

export interface UserDeleteApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  multiUserTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
}

export class UserDeleteApi {
  private readonly src;
  private readonly router: aws_apigateway.Resource;
  private readonly httpMethod: string;
  private readonly scope: Construct;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly multiUserTable: aws_dynamodb.Table;

  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UserDeleteApiProps) {
    this.scope = scope;
    this.httpMethod = props.httpMethod;
    this.src = props.srcRoot;
    this.baseId = id;
    this.router = props.router;
    this.layer = props.commonLayer;
    this.multiUserTable = props.multiUserTable;

    this.deleteUserApi();
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
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
      ],
      resources: [
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

  private deleteUserApi() {
    const lambdaFunction = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      functionName: `${this.baseId}-delete`,
      entry: `${this.src}/multi_users`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'multi_users_api.py',
      handler: 'delete_user',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        MULTI_USER_TABLE: this.multiUserTable.tableName,
      },
      layers: [this.layer],
    });
    const upsertUserIntegration = new apigw.LambdaIntegration(
      lambdaFunction,
      {
        proxy: false,
        requestParameters: {
          'integration.request.path.username': 'method.request.path.username',
        },
        requestTemplates: {
          'application/json': '{\n' +
              '    "pathStringParameters": {\n' +
              '        #foreach($pathParam in $input.params().path.keySet())\n' +
              '        "$pathParam": "$util.escapeJavaScript($input.params().path.get($pathParam))"\n' +
              '        #if($foreach.hasNext),#end\n' +
              '        #end\n' +
              '    }\n' +
              '}',
        },
        integrationResponses: [{ statusCode: '200' }],
      },
    );
    const userRouter = this.router.addResource('{username}');
    userRouter.addMethod(this.httpMethod, upsertUserIntegration, <MethodOptions>{
      apiKeyRequired: true,
      requestParameters: {
        'method.request.path.username': true,
      },
      methodResponses: [{
        statusCode: '200',
      }, { statusCode: '500' }],
    });
  }
}

