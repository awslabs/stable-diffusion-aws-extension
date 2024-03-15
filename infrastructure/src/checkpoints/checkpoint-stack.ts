import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_s3, CfnParameter, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { BucketDeploymentProps } from 'aws-cdk-lib/aws-s3-deployment';
import { Construct } from 'constructs';
import { CreateCheckPointApi } from '../api/checkpoints/create-chekpoint';
import { DeleteCheckpointsApi, DeleteCheckpointsApiProps } from '../api/checkpoints/delete-checkpoints';
import { ListCheckPointsApi } from '../api/checkpoints/list-chekpoints';
import { UpdateCheckPointApi } from '../api/checkpoints/update-chekpoint';
// import { Database } from '../shared/database';
import { Table } from 'aws-cdk-lib/aws-dynamodb';

// ckpt -> create_model -> model -> training -> ckpt -> inference
export interface CheckpointStackProps extends StackProps {
  // database: Database;
  checkpointTable: Table;
  multiUserTable: Table;
  routers: { [key: string]: Resource };
  s3Bucket: aws_s3.Bucket;
  commonLayer: PythonLayerVersion;
  logLevel: CfnParameter;
}

export class CheckpointStack {
  private readonly srcRoot = '../middleware_api/lambda';
  private readonly id: string;

  constructor(scope: Construct, id: string, props: CheckpointStackProps) {
    this.id = id;

    // Upload api template file to the S3 bucket
    new s3deploy.BucketDeployment(scope, `${this.id}-DeployApiTemplate`, <BucketDeploymentProps>{
      sources: [s3deploy.Source.asset(`${this.srcRoot}/common/template`)],
      destinationBucket: props.s3Bucket,
      destinationKeyPrefix: 'template',
    });

    const commonLayer = props.commonLayer;
    const routers = props.routers;

    const checkPointTable = props.checkpointTable;
    const multiUserTable = props.multiUserTable;

    // GET /checkpoints
    new ListCheckPointsApi(scope, `${this.id}-ListCheckPoints`, {
      s3Bucket: props.s3Bucket,
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'GET',
      router: routers.checkpoints,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
      logLevel: props.logLevel,
    });

    // POST /checkpoint
    const createCheckPointApi= new CreateCheckPointApi(scope, `${this.id}-CreateCheckPoint`, {
      checkpointTable: checkPointTable,
      commonLayer: commonLayer,
      httpMethod: 'POST',
      router: routers.checkpoints,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
      multiUserTable: multiUserTable,
      logLevel: props.logLevel,
    });

    // PUT /checkpoints/{id}
    const updateCheckPointApi = new UpdateCheckPointApi(scope, `${this.id}-UpdateCheckPoint`, {
      checkpointTable: checkPointTable,
      userTable: multiUserTable,
      commonLayer: commonLayer,
      httpMethod: 'PUT',
      router: routers.checkpoints,
      s3Bucket: props.s3Bucket,
      srcRoot: this.srcRoot,
      logLevel: props.logLevel,
    });
    updateCheckPointApi.model.node.addDependency(createCheckPointApi.model);
    updateCheckPointApi.requestValidator.node.addDependency(createCheckPointApi.requestValidator);

    // DELETE /checkpoints
    const deleteCheckpointsApi = new DeleteCheckpointsApi(
      scope, `${this.id}-DeleteCheckpoints`,
            <DeleteCheckpointsApiProps>{
              router: props.routers.checkpoints,
              commonLayer: props.commonLayer,
              checkPointsTable: checkPointTable,
              userTable: multiUserTable,
              httpMethod: 'DELETE',
              s3Bucket: props.s3Bucket,
              srcRoot: this.srcRoot,
              logLevel: props.logLevel,
            },
    );
    deleteCheckpointsApi.model.node.addDependency(updateCheckPointApi.model);
    deleteCheckpointsApi.requestValidator.node.addDependency(updateCheckPointApi.requestValidator);
  }
}
