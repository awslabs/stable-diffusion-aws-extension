import { App, Stack, StackProps, Aspects, CfnParameter, CfnOutput } from 'aws-cdk-lib';
import {
  BootstraplessStackSynthesizer,
  CompositeECRRepositoryAspect,
} from 'cdk-bootstrapless-synthesizer';
import { Construct } from 'constructs';
import { ECR_IMAGE_TAG } from './common/dockerImageTag';
import { SDAsyncInferenceStackProps, SDAsyncInferenceStack } from './sd-inference/sd-async-inference-stack';
import { SdTrainDeployStack } from './sd-train/sd-train-deploy-stack';
import { LambdaCommonLayer } from './shared/common-layer';
import { Database } from './shared/database';
import { RestApiGateway } from './shared/rest-api-gateway';
import { S3BucketStore } from './shared/s3-bucket';
import { SnsTopics } from './shared/sns-topics';

const app = new App();

export class Middleware extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: StackProps = {
      // env: devEnv,
      synthesizer: synthesizer(),
    },
  ) {
    super(scope, id, props);
    this.templateOptions.description = '(SO8032) - Stable-Diffusion AWS Extension';

    const apiKeyParam = new CfnParameter(this, 'sd-extension-api-key', {
      type: 'String',
      description: 'Enter a string of 20 characters that includes a combination of alphanumeric characters',
      allowedPattern: '[A-Za-z0-9]+',
      minLength: 20,
      maxLength: 20,
      // API Key value should be at least 20 characters
      default: '09876543210987654321',
    });

    const utilInstanceType = new CfnParameter(this, 'utils-cpu-inst-type', {
      type: 'String',
      description: 'ec2 instance type for operation including ckpt merge, model create etc.',
      allowedValues: ['ml.r5.large', 'ml.r5.xlarge', 'ml.c6i.2xlarge', 'ml.c6i.4xlarge'],
      // API Key value should be at least 20 characters
      default: 'ml.r5.large',
    });

    // Create CfnParameters here
    const emailParam = new CfnParameter(this, 'email', {
      type: 'String',
      description: 'Email address to receive notifications',
      allowedPattern: '\\w[-\\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\\.)+[A-Za-z]{2,14}',
      default: 'example@example.com',
    });

    const ecrImageTagParam = new CfnParameter(this, 'ecr_image_tag', {
      type: 'String',
      description: 'Public ECR Image tag, example: stable|dev',
      default: ECR_IMAGE_TAG,
    });

    const ddbTables = new Database(this, 'sd-ddb');

    const commonLayers = new LambdaCommonLayer(this, 'sd-common-layer', '../middleware_api/lambda');
    const api_train_path = 'train-api/train';
    const restApi = new RestApiGateway(this, apiKeyParam.valueAsString, [
      'model',
      'models',
      'checkpoint',
      'checkpoints',
      'train',
      'trains',
      'dataset',
      'datasets',
      'inference',
      'inference-api',
      api_train_path,
    ]);

    const s3BucketStore = new S3BucketStore(this, 'sd-s3');
    const snsTopics = new SnsTopics(this, 'sd-sns', emailParam);

    new SdTrainDeployStack(this, 'SdDreamBoothTrainStack', {
      commonLayer: commonLayers.commonLayer,
      // env: devEnv,
      synthesizer: props.synthesizer,
      modelInfInstancetype: utilInstanceType.valueAsString,
      ecr_image_tag: ecrImageTagParam.valueAsString,
      database: ddbTables,
      routers: restApi.routers,
      s3Bucket: s3BucketStore.s3Bucket,
      snsTopic: snsTopics.snsTopic,
    });


    new SDAsyncInferenceStack(
      this,
      'SdAsyncInferenceStack-dev',
            <SDAsyncInferenceStackProps>{
              // env: devEnv,
              synthesizer: props.synthesizer,
              s3_bucket: s3BucketStore.s3Bucket,
              training_table: ddbTables.trainingTable,
              snsTopic: snsTopics.snsTopic,
              ecr_image_tag: ecrImageTagParam.valueAsString,
              sd_inference_job_table: ddbTables.inferenceJobTable,
              sd_endpoint_deployment_job_table: ddbTables.endpointDeploymentJobTable,
              commonLayer: commonLayers.commonLayer,
              checkpointTable: ddbTables.checkPointTable,
              routers: restApi.routers,
            },
    );

    // Adding Outputs for apiGateway and s3Bucket
    new CfnOutput(this, 'ApiGatewayUrl', {
      value: restApi.apiGateway.url,
      description: 'API Gateway URL',
    });

    new CfnOutput(this, 'ApiGatewayUrlToken', {
      value: apiKeyParam.valueAsString,
      description: 'API Gateway Token',
    });

    new CfnOutput(this, 'S3BucketName', {
      value: s3BucketStore.s3Bucket.bucketName,
      description: 'S3 Bucket Name',
    });

    new CfnOutput(this, 'SNSTopicName', {
      value: snsTopics.snsTopic.topicName,
      description: 'SNS Topic Name to get train and inference result notification',
    });
  }
}

new Middleware(
  app,
  'Stable-diffusion-aws-extension-middleware-stack',
  {
    // env: devEnv,
    synthesizer: synthesizer(),
  },
);

app.synth();
// below lines are required if your application has Docker assets
if (process.env.USE_BSS) {
  Aspects.of(app).add(new CompositeECRRepositoryAspect());
}

function synthesizer() {
  return process.env.USE_BSS
    ? new BootstraplessStackSynthesizer()
    : undefined;
}
