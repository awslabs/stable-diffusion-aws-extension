import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_dynamodb, NestedStack, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';


export interface MultiUsersStackProps extends StackProps {
  multiUserTable: aws_dynamodb.Table;
  routers: {[key: string]: Resource};
  commonLayer: PythonLayerVersion;
}

export class MultiUsersStack extends NestedStack {
  constructor(scope: Construct, id: string, props: MultiUsersStackProps) {
    super(scope, id, props);


  }
}