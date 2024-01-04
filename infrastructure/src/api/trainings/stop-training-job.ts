import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_apigateway as apigw,
  aws_apigateway,
  aws_dynamodb,
  aws_iam,
  aws_lambda,
  CfnParameter,
  Duration,
} from 'aws-cdk-lib';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface StopTrainingJobApiProps {
  router: aws_apigateway.Resource;
  httpMethod: string;
  trainTable: aws_dynamodb.Table;
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
  private readonly trainTable: aws_dynamodb.Table;
  private readonly logLevel: CfnParameter;

  constructor(scope: Construct, id: string, props: StopTrainingJobApiProps) {
    this.id = id;
    this.scope = scope;
    this.srcRoot = props.srcRoot;
    this.layer = props.commonLayer;
    this.httpMethod = props.httpMethod;
    this.router = props.router;
    this.trainTable = props.trainTable;
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
      ],
      resources: [
        this.trainTable.tableArn,
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
    const lambdaFunction = new PythonFunction(this.scope, `${this.id}-lambda`, <PythonFunctionProps>{
      entry: `${this.srcRoot}/trainings`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'stop_training_job.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.getLambdaRole(),
      memorySize: 1024,
      environment: {
        TRAIN_TABLE: this.trainTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });

    const integration = new apigw.LambdaIntegration(
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
