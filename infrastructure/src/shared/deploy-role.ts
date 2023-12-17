import { CfnCondition, Fn, RemovalPolicy } from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export const LAMBDA_START_DEPLOY_ROLE_NAME = 'LambdaStartDeployRole';

export class LambdaDeployRoleStack {

  constructor(scope: Construct, useExist: string) {

    const createRole = new CfnCondition(
      scope,
      'InferenceStackShouldCreateSmRoleCondition',
      {
        expression: Fn.conditionEquals(useExist, 'no'),
      },
    );

    const newLambdaStartDeployRole = new iam.Role(scope, 'newLambdaStartDeployRole', {
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('sagemaker.amazonaws.com'),
      ),
      roleName: LAMBDA_START_DEPLOY_ROLE_NAME,
    });
    (newLambdaStartDeployRole.node.defaultChild as iam.CfnRole).cfnOptions.condition = createRole;
    newLambdaStartDeployRole.applyRemovalPolicy(RemovalPolicy.RETAIN);

  }

}
