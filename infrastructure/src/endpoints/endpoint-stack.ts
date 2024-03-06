import * as path from 'path';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_dynamodb,
  aws_sns,
  CfnParameter,
  StackProps,
} from 'aws-cdk-lib';

import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';
import { CreateEndpointApi, CreateEndpointApiProps } from '../api/endpoints/create-endpoint';
import { DeleteEndpointsApi, DeleteEndpointsApiProps } from '../api/endpoints/delete-endpoints';
import { ListEndpointsApi, ListEndpointsApiProps } from '../api/endpoints/list-endpoints';
import { SagemakerEndpointEvents, SagemakerEndpointEventsProps } from '../events/endpoints-event';

/*
AWS CDK code to create API Gateway, Lambda and SageMaker inference endpoint for txt2img/img2img inference
based on Stable Diffusion. S3 is used to store large payloads and passed as object reference in the API Gateway
request and Lambda function to avoid request payload limitation
Note: Sync Inference is put here for reference, we use Async Inference now
*/
export interface EndpointStackProps extends StackProps {
  inferenceErrorTopic: sns.Topic;
  inferenceResultTopic: sns.Topic;
  routers: { [key: string]: Resource };
  s3Bucket: s3.Bucket;
  trainingTable: dynamodb.Table;
  multiUserTable: dynamodb.Table;
  snsTopic: aws_sns.Topic;
  sd_inference_job_table: aws_dynamodb.Table;
  EndpointDeploymentJobTable: aws_dynamodb.Table;
  checkpointTable: aws_dynamodb.Table;
  commonLayer: PythonLayerVersion;
  logLevel: CfnParameter;
  ecrUrl: string;
}

export class EndpointStack {
  private readonly id: string;

  constructor(
    scope: Construct,
    id: string,
    props: EndpointStackProps,
  ) {
    this.id = id;
    const inferenceECR_url = props.ecrUrl;

    const srcRoot = '../middleware_api/lambda';

    new ListEndpointsApi(
      scope, `${this.id}-ListEndpoints`,
            <ListEndpointsApiProps>{
              router: props.routers.endpoints,
              commonLayer: props.commonLayer,
              endpointDeploymentTable: props.EndpointDeploymentJobTable,
              multiUserTable: props.multiUserTable,
              httpMethod: 'GET',
              srcRoot: srcRoot,
              logLevel: props.logLevel,
            },
    );

    const deleteEndpointsApi = new DeleteEndpointsApi(
      scope, `${this.id}-DeleteEndpoints`,
            <DeleteEndpointsApiProps>{
              router: props.routers.endpoints,
              commonLayer: props.commonLayer,
              endpointDeploymentTable: props.EndpointDeploymentJobTable,
              multiUserTable: props.multiUserTable,
              httpMethod: 'DELETE',
              srcRoot: srcRoot,
              logLevel: props.logLevel,
            },
    );

    new SagemakerEndpointEvents(
      scope, `${this.id}-EndpointEvents`,
            <SagemakerEndpointEventsProps>{
              commonLayer: props.commonLayer,
              endpointDeploymentTable: props.EndpointDeploymentJobTable,
              multiUserTable: props.multiUserTable,
              srcRoot: srcRoot,
              logLevel: props.logLevel,
            },
    );

    const createEndpointApi= new CreateEndpointApi(
      scope, `${this.id}-CreateEndpoint`,
            <CreateEndpointApiProps>{
              router: props.routers.endpoints,
              commonLayer: props.commonLayer,
              endpointDeploymentTable: props.EndpointDeploymentJobTable,
              multiUserTable: props.multiUserTable,
              inferenceJobTable: props.sd_inference_job_table,
              httpMethod: 'POST',
              srcRoot: srcRoot,
              s3Bucket: props.s3Bucket,
              userNotifySNS: props.snsTopic,
              inferenceECRUrl: inferenceECR_url,
              inferenceResultTopic: props.inferenceResultTopic,
              inferenceResultErrorTopic: props.inferenceErrorTopic,
              logLevel: props.logLevel,
            },
    );
    createEndpointApi.model.node.addDependency(deleteEndpointsApi.model);
    createEndpointApi.requestValidator.node.addDependency(deleteEndpointsApi.requestValidator);

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
