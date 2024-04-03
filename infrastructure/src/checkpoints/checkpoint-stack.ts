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

  constructor(scope: Construct, props: CheckpointStackProps) {

    // GET /checkpoints
    new ListCheckPointsApi(scope, 'ListCheckPoints', {
      checkpointTable: props.checkpointTable,
      commonLayer: props.commonLayer,
      httpMethod: 'GET',
      router: props.routers.checkpoints,
      multiUserTable: props.multiUserTable,
    });

    // POST /checkpoint
    new CreateCheckPointApi(scope, 'CreateCheckPoint', {
      checkpointTable: props.checkpointTable,
      commonLayer: props.commonLayer,
      httpMethod: 'POST',
      router: props.routers.checkpoints,
      s3Bucket: props.s3Bucket,
      multiUserTable: props.multiUserTable,
    });

    // PUT /checkpoints/{id}
    new UpdateCheckPointApi(scope, 'UpdateCheckPoint', {
      checkpointTable: props.checkpointTable,
      userTable: props.multiUserTable,
      commonLayer: props.commonLayer,
      httpMethod: 'PUT',
      router: props.routers.checkpoints,
      s3Bucket: props.s3Bucket,
    });

    // DELETE /checkpoints
    new DeleteCheckpointsApi(scope, 'DeleteCheckpoints', {
      router: props.routers.checkpoints,
      commonLayer: props.commonLayer,
      checkPointsTable: props.checkpointTable,
      userTable: props.multiUserTable,
      httpMethod: 'DELETE',
      s3Bucket: props.s3Bucket,
    },
    );
  }
}
