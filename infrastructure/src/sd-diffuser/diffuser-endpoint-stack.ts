import { aws_ecr, NestedStack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { CreateDiffuserEcrImage } from './diffuser-ecr-image';
import { AIGC_WEBUI_INFERENCE_DIFFUSER } from '../common/dockerImages';


export interface DiffuserEndpointStackProps extends StackProps {
  diffUserImageTag: string;
  targetRepositoryName: string;
  dockerRepo: aws_ecr.Repository;
}

export class DiffuserEndpointStack extends NestedStack {
  constructor(scope: Construct, id: string, props: DiffuserEndpointStackProps) {
    super(scope, id, props);

    new CreateDiffuserEcrImage(this, id, {
      srcImage: `${AIGC_WEBUI_INFERENCE_DIFFUSER}:${props.diffUserImageTag}`,
      targetRepositoryName: props.targetRepositoryName,
      dockerRepo: props.dockerRepo,
    });
  }
}