import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_s3, CfnParameter, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Construct } from 'constructs';
import { Database } from './database';
import { CreateDatasetApi } from '../api/datasets/create-dataset';
import { DeleteDatasetsApi } from '../api/datasets/delete-datasets';
import { GetDatasetApi } from '../api/datasets/get-dataset';
import { ListDatasetsApi } from '../api/datasets/list-datasets';
import { UpdateDatasetApi } from '../api/datasets/update-dataset';

export interface DatasetProps extends StackProps {
  database: Database;
  routers: { [key: string]: Resource };
  s3Bucket: aws_s3.Bucket;
  commonLayer: PythonLayerVersion;
  logLevel: CfnParameter;
}

export class DatasetStack {
  private readonly srcRoot = '../middleware_api/lambda';


  constructor(scope: Construct, props: DatasetProps) {

    const commonLayer = props.commonLayer;
    const routers = props.routers;
    const multiUserTable = props.database.multiUserTable;


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
      logLevel: props.logLevel,
    });

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
      logLevel: props.logLevel,
    });
    updateDatasetApi.model.node.addDependency(createDatasetApi.model);
    updateDatasetApi.requestValidator.node.addDependency(createDatasetApi.requestValidator);

    // GET /datasets
    new ListDatasetsApi(scope, 'ListDatasets', {
      commonLayer: commonLayer,
      datasetInfoTable: props.database.datasetInfoTable,
      httpMethod: 'GET',
      router: routers.datasets,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
      logLevel: props.logLevel,
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
      logLevel: props.logLevel,
    });

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
      logLevel: props.logLevel,
    },
    );
    deleteDatasetsApi.model.node.addDependency(updateDatasetApi.model);
    deleteDatasetsApi.requestValidator.node.addDependency(updateDatasetApi.requestValidator);


  }
}
