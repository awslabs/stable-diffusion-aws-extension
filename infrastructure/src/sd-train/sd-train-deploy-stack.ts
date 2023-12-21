import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_apigateway, aws_s3, aws_sns, NestedStack, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { BucketDeploymentProps } from 'aws-cdk-lib/aws-s3-deployment';
import { Construct } from 'constructs';
import { CreateCheckPointApi } from '../api/checkpoints/create-chekpoint';
import { DeleteCheckpointsApi, DeleteCheckpointsApiProps } from '../api/checkpoints/delete-checkpoints';
import { ListCheckPointsApi } from '../api/checkpoints/list-chekpoints';
import { UpdateCheckPointApi } from '../api/checkpoints/update-chekpoint';
import { CreateDatasetApi } from '../api/datasets/create-dataset';
import { DeleteDatasetsApi, DeleteDatasetsApiProps } from '../api/datasets/delete-datasets';
import { GetDatasetApi } from '../api/datasets/get-dataset';
import { ListDatasetsApi } from '../api/datasets/list-datasets';
import { UpdateDatasetApi } from '../api/datasets/update-dataset';
import { CreateModelJobApi } from '../api/models/create-model';
import { DeleteModelsApi, DeleteModelsApiProps } from '../api/models/delete-models';
import { ListModelsApi } from '../api/models/list-models';
import { UpdateModelApi } from '../api/models/update-model';
import { CreateTrainingJobApi } from '../api/trainings/create-training-job';
import { DeleteTrainingJobsApi, DeleteTrainingJobsApiProps } from '../api/trainings/delete-training-jobs';
import { GetTrainingJobApi, GetTrainingJobApiProps } from '../api/trainings/get-training-job';
import { ListTrainingJobsApi } from '../api/trainings/list-training-jobs';
import { UpdateTrainingJobApi } from '../api/trainings/update-training-job';
import { Database } from '../shared/database';

// ckpt -> create_model -> model -> training -> ckpt -> inference
export interface SdTrainDeployStackProps extends StackProps {
  createModelSuccessTopic: aws_sns.Topic;
  createModelFailureTopic: aws_sns.Topic;
  modelInfInstancetype: string;
  ecr_image_tag: string;
  database: Database;
  routers: { [key: string]: Resource };
  s3Bucket: aws_s3.Bucket;
  snsTopic: aws_sns.Topic;
  commonLayer: PythonLayerVersion;
  authorizer: aws_apigateway.IAuthorizer;
}

export class SdTrainDeployStack extends NestedStack {
  private readonly srcRoot = '../middleware_api/lambda';

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

    const checkPointTable = props.database.checkpointTable;
    const multiUserTable = props.database.multiUserTable;

    // GET /trains
    new ListTrainingJobsApi(this, 'ListTrainingJobs', {
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.trainings,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      authorizer: props.authorizer,
    });

    // POST /train
    new CreateTrainingJobApi(this, 'CreateTrainingJob', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      modelTable: props.database.modelTable,
      router: routers.trainings,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
    });

    const trainJobRouter = routers.trainings.addResource('{id}');

    // PUT /train
    new UpdateTrainingJobApi(this, 'StartTrainingJob', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      modelTable: props.database.modelTable,
      router: trainJobRouter,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
      userTopic: snsTopic,
      ecr_image_tag: props.ecr_image_tag,
    });

    // POST /model
    new CreateModelJobApi(this, 'CreateModel', {
      router: routers.models,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      modelTable: props.database.modelTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      checkpointTable: checkPointTable,
      multiUserTable: multiUserTable,
    });

    // GET /models
    new ListModelsApi(this, 'ListModels', {
      router: routers.models,
      srcRoot: this.srcRoot,
      modelTable: props.database.modelTable,
      multiUserTable: multiUserTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
      authorizer: props.authorizer,
    });

    // PUT /model
    new UpdateModelApi(this, 'UpdateModel', {
      s3Bucket: s3Bucket,
      router: routers.models,
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
    new ListCheckPointsApi(this, 'ListCheckPoints', {
      s3Bucket: s3Bucket,
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.checkpoints,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
      authorizer: props.authorizer,
    });

    // POST /checkpoint
    new CreateCheckPointApi(this, 'CreateCheckPoint', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      router: routers.checkpoints,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // PUT /checkpoint
    new UpdateCheckPointApi(this, 'UpdateCheckPoint', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      router: routers.checkpoints,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });

    // POST /dataset
    new CreateDatasetApi(this, 'CreateDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      httpMethod: 'POST',
      router: routers.datasets,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // PUT /dataset
    const updateDataset = new UpdateDatasetApi(this, 'UpdateDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      httpMethod: 'PUT',
      router: routers.datasets,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
    });

    // GET /datasets
    new ListDatasetsApi(this, 'ListDatasets', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      httpMethod: 'GET',
      router: routers.datasets,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
      multiUserTable: multiUserTable,
    });

    // GET /dataset/{dataset_name}/data
    new GetDatasetApi(this, 'GetDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemsTable: props.database.datasetItemTable,
      multiUserTable: multiUserTable,
      httpMethod: 'GET',
      router: updateDataset.router,
      s3Bucket: s3Bucket,
      srcRoot: this.srcRoot,
      authorizer: props.authorizer,
    });

    new DeleteCheckpointsApi(
      this, 'DeleteCheckpoints',
            <DeleteCheckpointsApiProps>{
              router: props.routers.checkpoints,
              commonLayer: props.commonLayer,
              checkPointsTable: checkPointTable,
              httpMethod: 'DELETE',
              s3Bucket: s3Bucket,
              srcRoot: this.srcRoot,
            },
    );

    new DeleteDatasetsApi(
      this, 'DeleteDatasets',
            <DeleteDatasetsApiProps>{
              router: props.routers.datasets,
              commonLayer: props.commonLayer,
              datasetInfoTable: props.database.datasetInfoTable,
              datasetItemTable: props.database.datasetItemTable,
              httpMethod: 'DELETE',
              s3Bucket: s3Bucket,
              srcRoot: this.srcRoot,
            },
    );

    new DeleteModelsApi(
      this, 'DeleteModels',
            <DeleteModelsApiProps>{
              router: props.routers.models,
              commonLayer: props.commonLayer,
              modelTable: props.database.modelTable,
              httpMethod: 'DELETE',
              s3Bucket: s3Bucket,
              srcRoot: this.srcRoot,
            },
    );

    new DeleteTrainingJobsApi(
      this, 'DeleteTrainingJobs',
            <DeleteTrainingJobsApiProps>{
              router: props.routers.trainings,
              commonLayer: props.commonLayer,
              trainingTable: props.database.trainingTable,
              httpMethod: 'DELETE',
              s3Bucket: s3Bucket,
              srcRoot: this.srcRoot,
            },
    );

    new GetTrainingJobApi(
      this, 'GetTrainingJob',
            <GetTrainingJobApiProps>{
              router: trainJobRouter,
              commonLayer: props.commonLayer,
              trainingTable: props.database.trainingTable,
              httpMethod: 'GET',
              s3Bucket: s3Bucket,
              srcRoot: this.srcRoot,
            },
    );

  }
}
