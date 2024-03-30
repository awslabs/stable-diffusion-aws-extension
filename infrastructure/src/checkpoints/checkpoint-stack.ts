import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { aws_s3, CfnParameter, StackProps } from 'aws-cdk-lib';
import { Resource } from 'aws-cdk-lib/aws-apigateway/lib/resource';
import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';
import { CreateCheckPointApi } from '../api/checkpoints/create-chekpoint';
import { DeleteCheckpointsApi } from '../api/checkpoints/delete-checkpoints';
import { ListCheckPointsApi } from '../api/checkpoints/list-chekpoints';
import { UpdateCheckPointApi } from '../api/checkpoints/update-chekpoint';

export interface CheckpointStackProps extends StackProps {
  checkpointTable: Table;
  multiUserTable: Table;
  routers: { [key: string]: Resource };
  s3Bucket: aws_s3.Bucket;
  commonLayer: PythonLayerVersion;
  logLevel: CfnParameter;
}

export class CheckpointStack {
  private readonly srcRoot = '../middleware_api/lambda';

  constructor(scope: Construct, props: CheckpointStackProps) {

    const commonLayer = props.commonLayer;
    const routers = props.routers;

    const checkPointTable = props.checkpointTable;
    const multiUserTable = props.multiUserTable;

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
    deleteCheckpointsApi.model.node.addDependency(updateCheckPointApi.model);
    deleteCheckpointsApi.requestValidator.node.addDependency(updateCheckPointApi.requestValidator);
  }
}
