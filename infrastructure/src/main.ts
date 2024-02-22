import { App, Aspects, Aws, CfnCondition, CfnOutput, CfnParameter, Fn, Stack, StackProps, Tags } from 'aws-cdk-lib';
import { CfnRestApi } from 'aws-cdk-lib/aws-apigateway';
import { Bucket } from 'aws-cdk-lib/aws-s3';
import { BootstraplessStackSynthesizer, CompositeECRRepositoryAspect } from 'cdk-bootstrapless-synthesizer';
import { Construct } from 'constructs';
import { PingApi } from './api/service/ping';
import { ECR_IMAGE_TAG } from './common/dockerImageTag';
import { SDAsyncInferenceStack, SDAsyncInferenceStackProps } from './sd-inference/sd-async-inference-stack';
import { SdTrainDeployStack } from './sd-train/sd-train-deploy-stack';
import { MultiUsersStack } from './sd-users/multi-users-stack';
import { LambdaCommonLayer } from './shared/common-layer';
import { Database } from './shared/database';
import { ResourceProvider } from './shared/resource-provider';
import { RestApiGateway } from './shared/rest-api-gateway';
import { AuthorizerLambda } from './shared/sd-authorizer-lambda';
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

    const apiKeyParam = new CfnParameter(this, 'SdExtensionApiKey', {
      type: 'String',
      description: 'Enter a string of 20 characters that includes a combination of alphanumeric characters',
      allowedPattern: '[A-Za-z0-9]+',
      minLength: 20,
      maxLength: 20,
      // API Key value should be at least 20 characters
      default: '09876543210987654321',
    });

    const utilInstanceType = new CfnParameter(this, 'UtilsCpuInstType', {
      type: 'String',
      description: 'ec2 instance type for operation including ckpt merge, model create etc.',
      allowedValues: ['ml.r5.large', 'ml.r5.xlarge', 'ml.c6i.2xlarge', 'ml.c6i.4xlarge'],
      // API Key value should be at least 20 characters
      default: 'ml.r5.large',
    });

    // Create CfnParameters here

    const s3BucketName = new CfnParameter(this, 'Bucket', {
      type: 'String',
      description: 'New bucket name or Existing Bucket name',
      minLength: 3,
      maxLength: 63,
      // Bucket naming rules: https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
      allowedPattern: '^(?!.*\\.\\.)(?!xn--)(?!sthree-)(?!.*-s3alias$)(?!.*--ol-s3$)(?!.*\\.$)(?!.*^\\.)[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$',
    });

    const emailParam = new CfnParameter(this, 'Email', {
      type: 'String',
      description: 'Email address to receive notifications',
      allowedPattern: '\\w[-\\w.+]*@([A-Za-z0-9][-A-Za-z0-9]+\\.)+[A-Za-z]{2,14}',
      default: 'example@example.com',
    });

    const ecrImageTagParam = new CfnParameter(this, 'EcrImageTag', {
      type: 'String',
      description: 'Public ECR Image tag, example: stable|dev',
      default: ECR_IMAGE_TAG,
    });

    const logLevel = new CfnParameter(this, 'LogLevel', {
      type: 'String',
      description: 'Log level, example: ERROR|INFO|DEBUG',
      default: 'ERROR',
      allowedValues: ['ERROR', 'INFO', 'DEBUG'],
    });

    // Create resources here

    // The solution currently does not support multi-region deployment, which makes it easy to failure.
    // Therefore, this resource is prioritized to save time.

    const resourceProvider = new ResourceProvider(
      this,
      'ResourcesProvider',
      {
        bucketName: s3BucketName.valueAsString,
        // when this version updated, resource manager will be executed
        version: '1.4.0',
      },
    );

    const s3Bucket = <Bucket>Bucket.fromBucketName(
      this,
      'aigc-bucket',
      resourceProvider.bucketName,
    );

    const ddbTables = new Database(this, 'sd-ddb');

    const commonLayers = new LambdaCommonLayer(this, 'sd-common-layer', '../middleware_api/lambda');

    const authorizerLambda = new AuthorizerLambda(this, 'sd-authorizer', {
      commonLayer: commonLayers.commonLayer,
      multiUserTable: ddbTables.multiUserTable,
    });

    const restApi = new RestApiGateway(this, apiKeyParam.valueAsString, [
      'ping',
      'models',
      'checkpoints',
      'datasets',
      'inference',
      'users',
      'roles',
      'endpoints',
      'inferences',
      'trainings',
    ]);
    const cfnApi = restApi.apiGateway.node.defaultChild as CfnRestApi;
    const isChinaCondition = new CfnCondition(this, 'IsChina', { expression: Fn.conditionEquals(Aws.PARTITION, 'aws-cn') });
    cfnApi.addPropertyOverride('EndpointConfiguration', {
      Types: [Fn.conditionIf(isChinaCondition.logicalId, 'REGIONAL', 'EDGE').toString()],
    });

    new MultiUsersStack(this, {
      synthesizer: props.synthesizer,
      commonLayer: commonLayers.commonLayer,
      multiUserTable: ddbTables.multiUserTable,
      routers: restApi.routers,
      passwordKeyAlias: authorizerLambda.passwordKeyAlias,
      authorizer: authorizerLambda.authorizer,
      logLevel,
    });

    new PingApi(this, 'Ping', {
      commonLayer: commonLayers.commonLayer,
      httpMethod: 'GET',
      router: restApi.routers.ping,
      srcRoot: '../middleware_api/lambda',
      logLevel,
    });

    const snsTopics = new SnsTopics(this, 'sd-sns', emailParam);

    new SDAsyncInferenceStack(this, <SDAsyncInferenceStackProps>{
      routers: restApi.routers,
      // env: devEnv,
      s3_bucket: s3Bucket,
      training_table: ddbTables.trainingTable,
      snsTopic: snsTopics.snsTopic,
      ecr_image_tag: ecrImageTagParam.valueAsString,
      sd_inference_job_table: ddbTables.sDInferenceJobTable,
      sd_endpoint_deployment_job_table: ddbTables.sDEndpointDeploymentJobTable,
      checkpointTable: ddbTables.checkpointTable,
      multiUserTable: ddbTables.multiUserTable,
      commonLayer: commonLayers.commonLayer,
      synthesizer: props.synthesizer,
      inferenceErrorTopic: snsTopics.inferenceResultErrorTopic,
      inferenceResultTopic: snsTopics.inferenceResultTopic,
      authorizer: authorizerLambda.authorizer,
      logLevel,
      resourceProvider,
    });

    new SdTrainDeployStack(this, {
      commonLayer: commonLayers.commonLayer,
      // env: devEnv,
      synthesizer: props.synthesizer,
      modelInfInstancetype: utilInstanceType.valueAsString,
      ecr_image_tag: ecrImageTagParam.valueAsString,
      database: ddbTables,
      routers: restApi.routers,
      s3Bucket: s3Bucket,
      snsTopic: snsTopics.snsTopic,
      createModelFailureTopic: snsTopics.createModelFailureTopic,
      createModelSuccessTopic: snsTopics.createModelSuccessTopic,
      authorizer: authorizerLambda.authorizer,
      logLevel,
      resourceProvider,
    });

    // Add ResourcesProvider dependency to all resources
    for (const resource of this.node.children) {
      if (!resourceProvider.instanceof(resource)) {
        resource.node.addDependency(resourceProvider.resources);
      }
    }

    // Add stackName tag to all resources
    const stackName = Stack.of(this).stackName;
    Tags.of(this).add('stackName', stackName);

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
      value: s3Bucket.bucketName,
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
  'Extension-for-Stable-Diffusion-on-AWS',
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
