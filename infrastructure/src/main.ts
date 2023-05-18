import { App, Stack, StackProps, Aspects, CfnParameter, CfnOutput } from 'aws-cdk-lib';
import {
  BootstraplessStackSynthesizer,
  CompositeECRRepositoryAspect,
} from 'cdk-bootstrapless-synthesizer';
import { Construct } from 'constructs';
import { SDAsyncInferenceStackProps, SDAsyncInferenceStack } from './sd-inference/sd-async-inference-stack';
import { SdTrainDeployStack } from './sd-train/sd-train-deploy-stack';
import * as crypto from 'crypto';

// for development, use account/region from cdk cli
// const devEnv = {
//   account: process.env.CDK_DEFAULT_ACCOUNT,
//   region: process.env.CDK_DEFAULT_REGION,
// };

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
    this.templateOptions.description = "(SO8032) - Stable-Diffusion AWS Extension";

    // Create CfnParameters here
    const emailParam = new CfnParameter(this, 'email', {
      type: 'String',
      description: 'Email address to receive notifications',
      allowedPattern: '\\w[-\\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\\.)+[A-Za-z]{2,14}',
      default: 'example@example.com',
    });

    // Create a short version of the UUID
    const shortUuid = crypto.randomBytes(4).toString('hex');
    // Create a timestamp
    let date = new Date();
    const formattedDate = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}-${date.getHours().toString().padStart(2, '0')}`;
    // Create a truncated or hashed version of the stack name
    const truncatedStackName = this.stackName.substring(0, 20);
    // Create the bucket name, making sure it's under 63 characters
    const defaultBucketName = `${truncatedStackName}-${shortUuid}-${formattedDate}`.toLowerCase();


    const bucketName = new CfnParameter(this, 'aigc-bucket-name', {
      type: 'String',
      description: 'Base bucket for aigc solution to use. Mainly for uploading data files and storing results',
      default: defaultBucketName.substring(0,63),
    });


    const trainStack = new SdTrainDeployStack(this, 'SdDreamBoothTrainStack', {
      // env: devEnv,
      synthesizer: props.synthesizer,
      emailParam: emailParam,
      bucketName: bucketName
    });

    const inferenceStack = new SDAsyncInferenceStack(
      this,
      'SdAsyncInferenceStack-dev',
            <SDAsyncInferenceStackProps>{
              // env: devEnv,
              api_gate_way: trainStack.apiGateway,
              s3_bucket: trainStack.s3Bucket,
              training_table: trainStack.trainingTable,
              snsTopic: trainStack.snsTopic,
              synthesizer: props.synthesizer,
              default_endpoint_name: trainStack.default_endpoint_name,
            },
    );

    inferenceStack.addDependency(trainStack);

    // Adding Outputs for apiGateway and s3Bucket
    new CfnOutput(this, 'ApiGatewayUrl', {
      value: trainStack.apiGateway.url,
      description: 'API Gateway URL',
    });

    new CfnOutput(this, 'S3BucketName', {
      value: trainStack.s3Bucket.bucketName,
      description: 'S3 Bucket Name',
    });

    new CfnOutput(this, 'SNSTopicName', {
      value: trainStack.snsTopic.topicName,
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
