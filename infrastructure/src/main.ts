import { App, Stack, StackProps, Aspects, CfnParameter } from 'aws-cdk-lib';
import {
  BootstraplessStackSynthesizer,
  CompositeECRRepositoryAspect,
} from 'cdk-bootstrapless-synthesizer';
import { Construct } from 'constructs';
import { SDAsyncInferenceStackProps, SDAsyncInferenceStack } from './sd-inference/sd-async-inference-stack';
import { SdTrainDeployStack } from './sd-train/sd-train-deploy-stack';

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

    const bucketName = new CfnParameter(this, 'aigc-bucket-name', {
      type: 'String',
      description: 'Base bucket for aigc solution to use. Mainly for uploading data files and storing results',
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
