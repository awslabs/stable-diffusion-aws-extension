import * as path from 'path';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_dynamodb, aws_sns, aws_sqs, StackProps } from 'aws-cdk-lib';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as sns from 'aws-cdk-lib/aws-sns';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { Construct } from 'constructs';
import { CreateEndpointApi } from '../api/endpoints/create-endpoint';
import { DeleteEndpointsApi } from '../api/endpoints/delete-endpoints';
import { ListEndpointsApi } from '../api/endpoints/list-endpoints';
import { SagemakerEndpointEvents } from '../events/endpoints-event';

/*
AWS CDK code to create API Gateway, Lambda and SageMaker inference endpoint for txt2img/img2img inference
based on Stable Diffusion. S3 is used to store large payloads and passed as object reference in the API Gateway
request and Lambda function to avoid request payload limitation
Note: Sync Inference is put here for reference, we use Async Inference now
*/
export interface EndpointStackProps extends StackProps {
  inferenceErrorTopic: sns.Topic;
  inferenceResultTopic: sns.Topic;
  executeResultSuccessTopic: sns.Topic;
  executeResultFailTopic: sns.Topic;
  routers: { [key: string]: Resource };
  s3Bucket: s3.Bucket;
  multiUserTable: dynamodb.Table;
  snsTopic: aws_sns.Topic;
  EndpointDeploymentJobTable: aws_dynamodb.Table;
  syncTable: aws_dynamodb.Table;
  instanceMonitorTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  accountId: ICfnRuleConditionExpression;
  queue: aws_sqs.Queue;
}

export class EndpointStack {

  constructor(
    scope: Construct,
    props: EndpointStackProps,
  ) {

    const srcRoot = '../middleware_api/lambda';

    new ListEndpointsApi(
      scope, 'ListEndpoints', {
        router: props.routers.endpoints,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: props.EndpointDeploymentJobTable,
        multiUserTable: props.multiUserTable,
        httpMethod: 'GET',
        srcRoot: srcRoot,
      },
    );

    new DeleteEndpointsApi(
      scope, 'DeleteEndpoints', {
        router: props.routers.endpoints,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: props.EndpointDeploymentJobTable,
        multiUserTable: props.multiUserTable,
        httpMethod: 'DELETE',
        srcRoot: srcRoot,
      },
    );

    new SagemakerEndpointEvents(
      scope, 'EndpointEvents', {
        commonLayer: props.commonLayer,
        endpointDeploymentTable: props.EndpointDeploymentJobTable,
        multiUserTable: props.multiUserTable,
        srcRoot: srcRoot,
      },
    );

    new CreateEndpointApi(
      scope, 'CreateEndpoint', {
        router: props.routers.endpoints,
        commonLayer: props.commonLayer,
        endpointDeploymentTable: props.EndpointDeploymentJobTable,
        multiUserTable: props.multiUserTable,
        syncTable: props.syncTable,
        instanceMonitorTable: props.instanceMonitorTable,
        httpMethod: 'POST',
        srcRoot: srcRoot,
        userNotifySNS: props.snsTopic,
        queue: props.queue,
        accountId: props.accountId,
        inferenceResultTopic: props.inferenceResultTopic,
        inferenceResultErrorTopic: props.inferenceErrorTopic,
        executeResultSuccessTopic: props.executeResultSuccessTopic,
        executeResultFailTopic: props.executeResultFailTopic,
      },
    );

    //adding model to data directory of s3 bucket
    if (props?.s3Bucket != undefined) {
      this.uploadModelToS3(scope, props.s3Bucket);
    }
  }

  private uploadModelToS3(scope: Construct, s3_bucket: s3.Bucket) {
    // Create a folder in the bucket
    const folderKey = 'data/';

    // Upload a local file to the created folder
    console.log(__dirname);
    const modelPath = path.resolve(__dirname, '../', '../', 'models', 'model.zip');
    new s3deploy.BucketDeployment(scope, 'DeployLocalFile', {
      sources: [s3deploy.Source.asset(modelPath)],
      destinationBucket: s3_bucket,
      destinationKeyPrefix: folderKey,
      retainOnDelete: false,
    });
  }
}
