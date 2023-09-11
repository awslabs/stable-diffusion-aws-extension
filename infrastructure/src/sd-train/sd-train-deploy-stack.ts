import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import {
  aws_s3,
  aws_sns,
  NestedStack,
  StackProps,
} from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { BucketDeploymentProps } from 'aws-cdk-lib/aws-s3-deployment';
import { Construct } from 'constructs';
import { CreateCheckPointApi } from './chekpoint-create-api';
import { UpdateCheckPointApi } from './chekpoint-update-api';
import { ListAllCheckPointsApi } from './chekpoints-listall-api';
import { CreateDatasetApi } from './dataset-create-api';
import { UpdateDatasetApi } from './dataset-update-api';
import { ListAllDatasetItemsApi } from './datasets-item-listall-api';
import { ListAllDatasetsApi } from './datasets-listall-api';
import { CreateModelJobApi } from './model-job-create-api';
import { ListAllModelJobApi } from './model-job-listall-api';
import { UpdateModelStatusRestApi } from './model-update-status-api';
import { CreateTrainJobApi } from './train-job-create-api';
import { ListAllTrainJobsApi } from './train-job-listall-api';
import { UpdateTrainJobApi } from './train-job-update-api';
import { Database } from '../shared/database';

// ckpt -> create_model -> model -> training -> ckpt -> inference
export interface SdTrainDeployStackProps extends StackProps {
  createModelSuccessTopic: aws_sns.Topic;
  createModelFailureTopic: aws_sns.Topic;
  modelInfInstancetype: string;
  ecr_image_tag: string;
  database: Database;
  routers: {[key: string]: Resource};
  s3Bucket: aws_s3.Bucket;
  snsTopic: aws_sns.Topic;
  commonLayer: PythonLayerVersion;
}

export class SdTrainDeployStack extends NestedStack {
  private readonly srcRoot='../middleware_api/lambda';

  constructor(scope: Construct, id: string, props: SdTrainDeployStackProps) {
    super(scope, id, props);
    // Use the parameters passed from Middleware
    const snsTopic = props.snsTopic;
    const s3Bucket = props.s3Bucket;

    // Upload api template file to the S3 bucket
    new s3deploy.BucketDeployment(this, 'DeployApiTemplate', <BucketDeploymentProps>{
      sources: [s3deploy.Source.asset(`${this.srcRoot}/common/template`)],
      destinationBucket: s3Bucket,
      destinationKeyPrefix: 'template',
    });

    const commonLayer = props.commonLayer;
    const routers = props.routers;

    // GET /trains
    new ListAllTrainJobsApi(this, 'sdExtn-trains', {
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.trains,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
    });
    const checkPointTable = props.database.checkpointTable;
    const multiUserTable = props.database.multiUserTable;
    // POST /train
    new CreateTrainJobApi(this, 'sdExtn-createTrain', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      modelTable: props.database.modelTable,
      router: [routers.train, routers['train-api/train']],
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
    });

    // PUT /train
    new UpdateTrainJobApi(this, 'sdExtn-putTrain', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      modelTable: props.database.modelTable,
      router: routers.train,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
      userTopic: snsTopic,
      ecr_image_tag: props.ecr_image_tag,
    });

    // POST /model
    new CreateModelJobApi(this, 'sdExtn-createModel', {
      router: routers.model,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      modelTable: props.database.modelTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      checkpointTable: checkPointTable,
    });

    // GET /models
    new ListAllModelJobApi(this, 'sdExtn-listallModel', {
      router: routers.models,
      srcRoot: this.srcRoot,
      modelTable: props.database.modelTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
    });

    // PUT /model
    new UpdateModelStatusRestApi(this, 'sdExtn-updateModel', {
      s3Bucket: s3Bucket,
      router: routers.model,
      httpMethod: 'PUT',
      commonLayer: commonLayer,
      srcRoot: this.srcRoot,
      modelTable: props.database.modelTable,
      snsTopic: snsTopic,
      checkpointTable: checkPointTable,
      trainMachineType: props.modelInfInstancetype,
      ecr_image_tag: props.ecr_image_tag,
      createModelFailureTopic: props.createModelFailureTopic,
      createModelSuccessTopic: props.createModelSuccessTopic,
    });

    // this.default_endpoint_name = modelStatusRestApi.sagemakerEndpoint.modelEndpoint.attrEndpointName;

    // GET /checkpoints
    new ListAllCheckPointsApi(this, 'sdExtn-listAllCkpts', {
      s3Bucket: s3Bucket,
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.checkpoints,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // POST /checkpoint
    new CreateCheckPointApi(this, 'sdExtn-createCkpt', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      router: routers.checkpoint,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // PUT /checkpoint
    new UpdateCheckPointApi(this, 'sdExtn-updateCkpt', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      router: routers.checkpoint,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });

    // POST /dataset
    new CreateDatasetApi(this, 'sdExtn-createDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      httpMethod: 'POST',
      router: routers.dataset,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });

    // PUT /dataset
    new UpdateDatasetApi(this, 'sdExtn-updateDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      httpMethod: 'PUT',
      router: routers.dataset,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });

    // GET /datasets
    new ListAllDatasetsApi(this, 'sdExtn-listallDatasets', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      httpMethod: 'GET',
      router: routers.datasets,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });

    // GET /dataset/{dataset_name}/data
    new ListAllDatasetItemsApi(this, 'sdExtn-listallDsItems', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemsTable: props.database.datasetItemTable,
      httpMethod: 'GET',
      router: routers.dataset,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });
  }
}
