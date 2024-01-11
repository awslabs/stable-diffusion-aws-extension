import { PythonFunction, PythonFunctionProps } from '@aws-cdk/aws-lambda-python-alpha';
import {
  Aws,
  aws_apigateway as apigw,
  aws_dynamodb,
  aws_ecr,
  aws_iam,
  aws_lambda,
  aws_s3,
  aws_sns,
  CfnParameter,
  CustomResource,
  Duration,
  RemovalPolicy,
} from 'aws-cdk-lib';
import { JsonSchemaType, JsonSchemaVersion, Model, RequestValidator } from 'aws-cdk-lib/aws-apigateway';
import { MethodOptions } from 'aws-cdk-lib/aws-apigateway/lib/method';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Effect } from 'aws-cdk-lib/aws-iam';
import { Architecture, Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import { DockerImageName, ECRDeployment } from '../../cdk-ecr-deployment/lib';
import { AIGC_WEBUI_UTILS } from '../../common/dockerImages';
import { CreateModelSageMakerEndpoint } from '../../sd-train/create-model-endpoint';
import { ResourceProvider } from '../../shared/resource-provider';


export interface UpdateModelApiProps {
  createModelFailureTopic: aws_sns.Topic;
  createModelSuccessTopic: aws_sns.Topic;
  httpMethod: string;
  router: Resource;
  modelTable: aws_dynamodb.Table;
  srcRoot: string;
  commonLayer: aws_lambda.LayerVersion;
  s3Bucket: aws_s3.Bucket;
  snsTopic: aws_sns.Topic;
  checkpointTable: aws_dynamodb.Table;
  trainMachineType: string;
  ecr_image_tag: string;
  logLevel: CfnParameter;
  resourceProvider: ResourceProvider;
}

export class UpdateModelApi {

  public readonly sagemakerEndpoint: CreateModelSageMakerEndpoint;
  private readonly imageUrl: string;
  private readonly machineType: string;
  private readonly resourceProvider: ResourceProvider;

  private readonly src;
  private readonly scope: Construct;
  private readonly modelTable: aws_dynamodb.Table;
  private readonly checkpointTable: aws_dynamodb.Table;
  private readonly layer: aws_lambda.LayerVersion;
  private readonly router: Resource;
  private readonly httpMethod: string;
  private readonly s3Bucket: aws_s3.Bucket;
  private readonly dockerRepo: aws_ecr.Repository;
  private readonly logLevel: CfnParameter;
  private readonly baseId: string;

  constructor(scope: Construct, id: string, props: UpdateModelApiProps) {
    this.scope = scope;
    this.router = props.router;
    this.baseId = id;
    this.machineType = props.trainMachineType;
    this.modelTable = props.modelTable;
    this.httpMethod = props.httpMethod;
    this.src = props.srcRoot;
    this.layer = props.commonLayer;
    this.s3Bucket = props.s3Bucket;
    this.checkpointTable = props.checkpointTable;
    this.imageUrl = AIGC_WEBUI_UTILS + props.ecr_image_tag;
    this.logLevel = props.logLevel;
    this.resourceProvider = props.resourceProvider;

    // create private image:
    const dockerDeployment = new CreateModelInferenceImage(this.scope, this.imageUrl);
    this.dockerRepo = dockerDeployment.dockerRepo;
    // create sagemaker endpoint
    this.sagemakerEndpoint = new CreateModelSageMakerEndpoint(this.scope, 'esd-utils', {
      machineType: this.machineType,
      outputFolder: 'models',
      primaryContainer: `${this.dockerRepo.repositoryUri}:latest`,
      s3OutputBucket: this.s3Bucket,
      commonLayer: this.layer,
      modelTable: this.modelTable,
      rootSrc: this.src,
      userSnsTopic: props.snsTopic,
      successTopic: props.createModelSuccessTopic,
      failureTopic: props.createModelFailureTopic,
      resourceProvider: this.resourceProvider,
    });
    this.sagemakerEndpoint.model.node.addDependency(dockerDeployment.customJob);
    // create lambda to trigger
    this.updateModelApi();
  }

  private iamRole(): aws_iam.Role {
    const newRole = new aws_iam.Role(this.scope, `${this.baseId}-role`, {
      assumedBy: new aws_iam.ServicePrincipal('lambda.amazonaws.com'),
    });
    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'dynamodb:BatchGetItem',
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:BatchWriteItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
      ],
      resources: [this.modelTable.tableArn, this.checkpointTable.tableArn],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'sagemaker:InvokeEndpointAsync',
      ],
      resources: [`arn:${Aws.PARTITION}:sagemaker:${Aws.REGION}:${Aws.ACCOUNT_ID}:endpoint/${this.sagemakerEndpoint.modelEndpoint.attrEndpointName}`],
    }));

    newRole.addToPolicy(new aws_iam.PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket',
        's3:CreateBucket',
        's3:AbortMultipartUpload',
        's3:ListMultipartUploadParts',
        's3:ListBucketMultipartUploads',
      ],
      resources: [
        `${this.s3Bucket.bucketArn}/*`,
        `arn:${Aws.PARTITION}:s3:::*SageMaker*`,
        `arn:${Aws.PARTITION}:s3:::*Sagemaker*`,
        `arn:${Aws.PARTITION}:s3:::*sagemaker*`,
      ],
    }));

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

  private updateModelApi() {
    const updateModelLambda = new PythonFunction(this.scope, `${this.baseId}-lambda`, <PythonFunctionProps>{
      entry: `${this.src}/models`,
      architecture: Architecture.X86_64,
      runtime: Runtime.PYTHON_3_9,
      index: 'update_model.py',
      handler: 'handler',
      timeout: Duration.seconds(900),
      role: this.iamRole(),
      memorySize: 1024,
      environment: {
        DYNAMODB_TABLE: this.modelTable.tableName,
        S3_BUCKET: this.s3Bucket.bucketName,
        SAGEMAKER_ENDPOINT_NAME: this.sagemakerEndpoint.modelEndpoint.attrEndpointName,
        CHECKPOINT_TABLE: this.checkpointTable.tableName,
        LOG_LEVEL: this.logLevel.valueAsString,
      },
      layers: [this.layer],
    });
    updateModelLambda.node.addDependency(this.sagemakerEndpoint.modelEndpoint);

    const updateModelLambdaIntegration = new apigw.LambdaIntegration(
      updateModelLambda,
      {
        proxy: true,
      },
    );

    const requestModel = new Model(this.scope, `${this.baseId}-model`, {
      restApi: this.router.api,
      modelName: this.baseId,
      description: `${this.baseId} Request Model`,
      schema: {
        schema: JsonSchemaVersion.DRAFT4,
        title: this.baseId,
        type: JsonSchemaType.OBJECT,
        properties: {
          status: {
            type: JsonSchemaType.STRING,
            minLength: 1,
          },
          multi_parts_tags: {
            type: JsonSchemaType.OBJECT,
          },
        },
        required: [
          'status',
          'multi_parts_tags',
        ],
      },
      contentType: 'application/json',
    });

    const requestValidator = new RequestValidator(
      this.scope,
      `${this.baseId}-validator`,
      {
        restApi: this.router.api,
        requestValidatorName: this.baseId,
        validateRequestBody: true,
      });

    this.router.addResource('{id}')
      .addMethod(this.httpMethod, updateModelLambdaIntegration, <MethodOptions>{
        apiKeyRequired: true,
        requestValidator,
        requestModels: {
          'application/json': requestModel,
        },
      });
  }
}


class CreateModelInferenceImage {

  public readonly ecrDeployment: ECRDeployment;
  public readonly dockerRepo: aws_ecr.Repository;
  public readonly customJob: CustomResource;
  private readonly id = 'aigc-createmodel-inf';

  constructor(scope: Construct, srcImage: string) {
    this.dockerRepo = new aws_ecr.Repository(scope, `${this.id}-repo`, {
      repositoryName: 'stable-diffusion-aws-extension/aigc-webui-utils',
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.ecrDeployment = new ECRDeployment(scope, `${this.id}-ecr-deploy`, {
      src: new DockerImageName(srcImage),
      dest: new DockerImageName(`${this.dockerRepo.repositoryUri}:latest`),
    });

    // trigger the lambda
    this.customJob = new CustomResource(scope, `${this.id}-cr-image`, {
      serviceToken: this.ecrDeployment.serviceToken,
      resourceType: 'Custom::AIGCSolutionECRLambda',
      properties: {
        SrcImage: `docker://${srcImage}`,
        DestImage: `docker://${this.dockerRepo.repositoryUri}:latest`,
        RepositoryName: `${this.dockerRepo.repositoryName}`,
      },
    });
    this.customJob.node.addDependency(this.ecrDeployment);
  }
}
