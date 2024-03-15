import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway,
  aws_iam,
  aws_lambda,
  CfnParameter,
  Duration,
} from 'aws-cdk-lib';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface StopTrainingJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  trainTable: Table;
  multiUserTable: Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  logLevel: CfnParameter;
}

export class StopTrainingJobApi {

  private readonly id: string;
  private readonly scope: Construct;
  private readonly srcRoot: string;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly httpMethod: string;
  private readonly router: aws_apigateway.Resource;
  private readonly trainTable: Table;
  private readonly multiUserTable: Table;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: StopTrainingJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.srcRoot = props.srcRoot;
    this.layer = props.commonLayer;
    this.httpMethod = props.httpMethod;
    this.router = props.router;
    this.trainTable = props.trainTable;
    this.multiUserTable = props.multiUserTable;
    this.logLevel = props.logLevel;

    this.stopTrainJobLambda();
  }


  private getLambdaRole(): aws_iam.Role {

    const newRole = new aws_iam.Role(this.scope, `${this.id}-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:GetItem',
        'dynamodb:UpdateItem',
        'dynamodb:BatchGetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
      ],
      resources: [
        this.trainTable.tableArn,
        this.multiUserTable.tableArn,
      ],
    }));

    newRole.attachInlinePolicy(
      new aws_iam.Policy(this.scope, `${this.id}-Policy`, {
        statements: [
          new aws_iam.PolicyStatement({
            actions: ['states:StopExecution'],
            effect: aws_iam.Effect.ALLOW,
            resources: ['*'],
          }),
        ],
      }),
    );

    newRole.addToPolicy(new aws_iam.PolicyStatement({
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

  private stopTrainJobLambda(): aws_lambda.IFunction {
    const lambdaFunction = new PythonFunction(this.scope, `${this.id}-lambda`, {
      entry: `${this.srcRoot}/trainings`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_10,
      index: 'stop_training_job.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.getLambdaRole(),
      memorySize: 2048,
      environment: {
        MULTI_USER_TABLE: this.multiUserTable.tableName,
        TRAIN_TABLE: this.trainTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const integration = new aws_apigateway.LambdaIntegration(
      lambdaFunction,
      {
        proxy: true,
      },
    );

    this.router.addResource('stop')
      .addMethod(this.httpMethod, integration, <MethodOptions>{
        apiKeyRequired: true,
      });

    return lambdaFunction;
  }


}
