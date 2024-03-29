import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_s3, aws_sns, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { ICfnRuleConditionExpression } from 'aws-cdk-lib/core/lib/cfn-condition';
import { Construct } from 'constructs';
import { Database } from './database';
import { ResourceProvider } from './resource-provider';
import { CreateCheckPointApi } from '../api/checkpoints/create-chekpoint';
import { DeleteCheckpointsApi } from '../api/checkpoints/delete-checkpoints';
import { ListCheckPointsApi } from '../api/checkpoints/list-chekpoints';
import { UpdateCheckPointApi } from '../api/checkpoints/update-chekpoint';
import { CreateDatasetApi } from '../api/datasets/create-dataset';
import { DeleteDatasetsApi } from '../api/datasets/delete-datasets';
import { GetDatasetApi } from '../api/datasets/get-dataset';
import { ListDatasetsApi } from '../api/datasets/list-datasets';
import { UpdateDatasetApi } from '../api/datasets/update-dataset';
import { CreateTrainingJobApi } from '../api/trainings/create-training-job';
import { DeleteTrainingJobsApi } from '../api/trainings/delete-training-jobs';
import { GetTrainingJobApi } from '../api/trainings/get-training-job';
import { ListTrainingJobsApi } from '../api/trainings/list-training-jobs';
import { SagemakerTrainingEvents } from '../events/trainings-event';

export interface TrainDeployProps extends StackProps {
  database: Database;
  routers: { [key: string]: Resource };
  s3Bucket: aws_s3.Bucket;
  snsTopic: aws_sns.Topic;
  commonLayer: PythonLayerVersion;
  resourceProvider: ResourceProvider;
  accountId: ICfnRuleConditionExpression;
}

export class TrainDeploy {
  public readonly deleteTrainingJobsApi: DeleteTrainingJobsApi;
  private readonly srcRoot = '../middleware_api/lambda';
  private readonly resourceProvider: ResourceProvider;

  constructor(scope: Construct, props: TrainDeployProps) {

    this.resourceProvider = props.resourceProvider;

    // Upload api template file to the S3 bucket
    new s3deploy.BucketDeployment(scope, 'DeployApiTemplate', {
      sources: [s3deploy.Source.asset(`${this.srcRoot}/common/template`)],
      destinationBucket: props.s3Bucket,
      destinationKeyPrefix: 'template',
    });

    const commonLayer = props.commonLayer;
    const routers = props.routers;

    const checkPointTable = props.database.checkpointTable;
    const multiUserTable = props.database.multiUserTable;

    // GET /trainings
    new ListTrainingJobsApi(scope, 'ListTrainingJobs', {
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.trainings,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
    });

    // POST /trainings
    const createTrainingJobApi = new CreateTrainingJobApi(scope, 'CreateTrainingJob', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      modelTable: props.database.modelTable,
      router: routers.trainings,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
      trainTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      userTopic: props.snsTopic,
      resourceProvider: this.resourceProvider,
      accountId: props.accountId,
      datasetInfoTable: props.database.datasetInfoTable,
    });

    // GET /checkpoints
    new ListCheckPointsApi(scope, 'ListCheckPoints', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.checkpoints,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // POST /checkpoint
    const createCheckPointApi = new CreateCheckPointApi(scope, 'CreateCheckPoint', {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      router: routers.checkpoints,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // PUT /checkpoints/{id}
    const updateCheckPointApi = new UpdateCheckPointApi(scope, 'UpdateCheckPoint', {
      checkpointTable: checkPointTable,
      userTable: multiUserTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      router: routers.checkpoints,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    });
    updateCheckPointApi.model.node.addDependency(createCheckPointApi.model);
    updateCheckPointApi.requestValidator.node.addDependency(createCheckPointApi.requestValidator);

    // POST /datasets
    const createDatasetApi = new CreateDatasetApi(scope, 'CreateDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      httpMethod: 'POST',
      router: routers.datasets,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });
    createDatasetApi.model.node.addDependency(updateCheckPointApi.model);
    createDatasetApi.requestValidator.node.addDependency(updateCheckPointApi.requestValidator);

    // PUT /datasets/{id}
    const updateDatasetApi = new UpdateDatasetApi(scope, 'UpdateDataset', {
      commonLayer: commonLayer,
      userTable: multiUserTable,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      httpMethod: 'PUT',
      router: routers.datasets,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    });
    updateDatasetApi.model.node.addDependency(createDatasetApi.model);
    updateDatasetApi.requestValidator.node.addDependency(createDatasetApi.requestValidator);

    // GET /datasets
    new ListDatasetsApi(scope, 'ListDatasets', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      httpMethod: 'GET',
      router: routers.datasets,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
    });

    // GET /dataset/{dataset_name}
    new GetDatasetApi(scope, 'GetDataset', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemsTable: props.database.datasetItemTable,
      multiUserTable: multiUserTable,
      httpMethod: 'GET',
      router: updateDatasetApi.router,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    });

    // DELETE /checkpoints
    const deleteCheckpointsApi = new DeleteCheckpointsApi(scope, 'DeleteCheckpoints', {
      router: props.routers.checkpoints,
      commonLayer: props.commonLayer,
      checkPointsTable: checkPointTable,
      userTable: multiUserTable,
      httpMethod: 'DELETE',
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    },
    );
    deleteCheckpointsApi.model.node.addDependency(updateDatasetApi.model);
    deleteCheckpointsApi.requestValidator.node.addDependency(updateDatasetApi.requestValidator);

    // DELETE /datasets
    const deleteDatasetsApi = new DeleteDatasetsApi(scope, 'DeleteDatasets', {
      router: props.routers.datasets,
      commonLayer: props.commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      datasetItemTable: props.database.datasetItemTable,
      multiUserTable: multiUserTable,
      httpMethod: 'DELETE',
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    },
    );
    deleteDatasetsApi.model.node.addDependency(deleteCheckpointsApi.model);
    deleteDatasetsApi.requestValidator.node.addDependency(deleteCheckpointsApi.requestValidator);

    // DELETE /trainings
    this.deleteTrainingJobsApi = new DeleteTrainingJobsApi(scope, 'DeleteTrainingJobs', {
      router: props.routers.trainings,
      commonLayer: props.commonLayer,
      trainingTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      httpMethod: 'DELETE',
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    },
    );
    this.deleteTrainingJobsApi.model.node.addDependency(createTrainingJobApi.model);
    this.deleteTrainingJobsApi.requestValidator.node.addDependency(createTrainingJobApi.requestValidator);

    // DELETE /trainings/{id}
    new GetTrainingJobApi(scope, 'GetTrainingJob', {
      router: props.routers.trainings,
      commonLayer: props.commonLayer,
      trainingTable: props.database.trainingTable,
      multiUserTable: multiUserTable,
      httpMethod: 'GET',
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
    },
    );

    new SagemakerTrainingEvents(scope, 'SagemakerTrainingEvents', {
      commonLayer: props.commonLayer,
      trainingTable: props.database.trainingTable,
      checkpointTable: props.database.checkpointTable,
      srcRoot: this.srcRoot,
      userTopic: props.snsTopic,
      s3Bucket: props.s3Bucket,
    },
    );

  }
}
