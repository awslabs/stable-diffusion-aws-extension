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
import { ComfyApiStack, ComfyInferenceStackProps } from './comfy/comfy-api-stack';
import { ComfyDatabase } from './comfy/comfy-database';
import { CheckpointStack } from './checkpoints/checkpoint-stack';

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
    const apiKeyComfyParam = new CfnParameter(this, 'ComfyExtensionApiKey', {
      type: 'String',
      description: 'Enter a string of 20 characters that includes a combination of alphanumeric characters',
      allowedPattern: '[A-Za-z0-9]+',
      minLength: 20,
      maxLength: 20,
      // API Key value should be at least 20 characters
      default: '09876543210987654321',
    });

    const scriptChoice = new CfnParameter(this, 'scriptChoose', {
      type: 'String',
      description: 'choose the choice you want',
      default: 'ALL',
      allowedValues: ['ComfyUI', 'WebUI', 'ALL'],
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

    const ecrComfyImageTagParam = new CfnParameter(this, 'ComfyEcrImageTag', {
      type: 'String',
      description: 'Public ComfyUI ECR Image tag, example: stable|dev',
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
        // when props updated, resource manager will be executed
        // ecrImageTag is not used in the resource manager
        // but if it changes, the resource manager will be executed with 'Update'
        // if the resource manager is executed, it will recheck and create resources for stack
        bucketName: s3BucketName.valueAsString,
        ecrImageTag: ecrImageTagParam.valueAsString,
      },
    );

    const s3Bucket = <Bucket>Bucket.fromBucketName(
      this,
      'aigc-bucket',
      resourceProvider.bucketName,
    );

    const ddbTables = new Database(this, 'sd-ddb');

    const commonLayers = new LambdaCommonLayer(this, 'sd-common-layer', '../middleware_api/lambda');

    const authorizerLambda = new AuthorizerLambda(this, 'sd-authorizer');

    const isComfyChoice = new CfnCondition(this, 'IsComfyChoice', {
      expression: Fn.conditionEquals(scriptChoice, 'ComfyUI'),
    });

    const isSdChoice = new CfnCondition(this, 'IsSdChoice', {
      expression: Fn.conditionEquals(scriptChoice, 'WebUI'),
    });

    const isWholeChoice = new CfnCondition(this, 'IsAllChoice', {
      expression: Fn.conditionEquals(scriptChoice, 'ALL'),
    });


    const isChinaCondition = new CfnCondition(this, 'IsChina', { expression: Fn.conditionEquals(Aws.PARTITION, 'aws-cn') });

    if (isWholeChoice || isSdChoice) {
      const restApi = new RestApiGateway(this, 'sd-extension', apiKeyParam.valueAsString, [
        'ping',
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
      cfnApi.addPropertyOverride('EndpointConfiguration', {
        Types: [Fn.conditionIf(isChinaCondition.logicalId, 'REGIONAL', 'EDGE').toString()],
      });
      new MultiUsersStack(this, {
        synthesizer: props.synthesizer,
        commonLayer: commonLayers.commonLayer,
        multiUserTable: ddbTables.multiUserTable,
        routers: restApi.routers,
        passwordKeyAlias: authorizerLambda.passwordKeyAlias,
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
        logLevel,
        resourceProvider,
      });

      new SdTrainDeployStack(this, {
        commonLayer: commonLayers.commonLayer,
        // env: devEnv,
        synthesizer: props.synthesizer,
        ecr_image_tag: ecrImageTagParam.valueAsString,
        database: ddbTables,
        routers: restApi.routers,
        s3Bucket: s3Bucket,
        snsTopic: snsTopics.snsTopic,
        createModelFailureTopic: snsTopics.createModelFailureTopic,
        createModelSuccessTopic: snsTopics.createModelSuccessTopic,
        logLevel,
        resourceProvider,
      });

      new CheckpointStack(this, {
        // env: devEnv,
        synthesizer: props.synthesizer,
        checkpointTable: ddbTables.checkpointTable,
        multiUserTable: ddbTables.multiUserTable,
        routers: restApi.routers,
        s3Bucket: s3Bucket,
        commonLayer: commonLayers.commonLayer,
        logLevel: logLevel,
      });
      // Adding Outputs for apiGateway and s3Bucket
      new CfnOutput(this, 'ApiGatewayUrl', {
        value: restApi.apiGateway.url,
        description: 'API Gateway URL',
      });
      new CfnOutput(this, 'SNSTopicName', {
        value: snsTopics.snsTopic.topicName,
        description: 'SNS Topic Name to get train and inference result notification',
      });
      new CfnOutput(this, 'ApiGatewayUrlToken', {
        value: apiKeyParam.valueAsString,
        description: 'API Gateway Token',
      });
    }
    if (isWholeChoice || isComfyChoice) {
      const ddbComfyTables = new ComfyDatabase(this, 'comfy-ddb');
      const inferenceEcrRepositoryUrl: string = 'comfy-aws-extension/gen-ai-comfy-inference';
      const restComfyApi = new RestApiGateway(this, 'comfy-extension', apiKeyComfyParam.valueAsString, [
        'template',
        'model',
        'execute',
        'node',
        'config',
        'endpoint',
        'sync',
      ]);
      const cfnApiComfy = restComfyApi.apiGateway.node.defaultChild as CfnRestApi;
      cfnApiComfy.addPropertyOverride('EndpointConfiguration', {
        Types: [Fn.conditionIf(isChinaCondition.logicalId, 'REGIONAL', 'EDGE').toString()],
      });
      const apis = new ComfyApiStack(this, 'comfy-api', <ComfyInferenceStackProps>{
        routers: restComfyApi.routers,
        // env: devEnv,
        s3Bucket: s3Bucket,
        ecrImageTag: ecrComfyImageTagParam.valueAsString,
        configTable: ddbComfyTables.configTable,
        executeTable: ddbComfyTables.executeTable,
        modelTable: ddbTables.checkpointTable,
        nodeTable: ddbComfyTables.nodeTable,
        msgTable: ddbComfyTables.msgTable,
        commonLayer: commonLayers.commonLayer,
        ecrRepositoryName: inferenceEcrRepositoryUrl,
        logLevel: logLevel,
        resourceProvider: resourceProvider,
      });
      apis.node.addDependency(ddbComfyTables);

      new CheckpointStack(this, {
        // env: devEnv,
        synthesizer: props.synthesizer,
        checkpointTable: ddbTables.checkpointTable,
        multiUserTable: ddbTables.multiUserTable,
        routers: restComfyApi.routers,
        s3Bucket: s3Bucket,
        commonLayer: commonLayers.commonLayer,
        logLevel: logLevel,
      });

      // Adding Outputs for apiGateway and s3Bucket
      new CfnOutput(this, 'ComfyApiGatewayUrl', {
        value: restComfyApi.apiGateway.url,
        description: 'API Gateway URL',
      });
      new CfnOutput(this, 'ComfyApiGatewayUrlToken', {
        value: apiKeyComfyParam.valueAsString,
        description: 'API Gateway Token',
      });
    }

    // Add ResourcesProvider dependency to all resources
    for (const resource of this.node.children) {
      if (!resourceProvider.instanceof(resource)) {
        resource.node.addDependency(resourceProvider.resources);
      }
    }

    // Add stackName tag to all resources
    const stackName = Stack.of(this).stackName;
    Tags.of(this).add('stackName', stackName);

    new CfnOutput(this, 'S3BucketName', {
      value: s3Bucket.bucketName,
      description: 'S3 Bucket Name',
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
