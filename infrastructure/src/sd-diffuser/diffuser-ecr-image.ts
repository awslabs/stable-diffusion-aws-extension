import { aws_ecr, CustomResource } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DockerImageName, ECRDeployment } from '../cdk-ecr-deployment/lib';

export interface CreateDiffuserEcrImageProps {
  srcImage: string;
  targetRepositoryName: string;
  dockerRepo: aws_ecr.Repository;
}

export class CreateDiffuserEcrImage {
  public readonly ecrDeployment: ECRDeployment;
  public readonly customJob: CustomResource;

  constructor(scope: Construct, id: string, props: CreateDiffuserEcrImageProps) {
    this.ecrDeployment = new ECRDeployment(scope, `${id}-du-ep`, {
      src: new DockerImageName(props.srcImage),
      dest: new DockerImageName(`${props.dockerRepo.repositoryUri}:default`),
    });

    this.customJob = new CustomResource(scope, `${id}-duImage`, {
      serviceToken: this.ecrDeployment.serviceToken,
      resourceType: 'Custom::AIGCSolutionECRLambda',
      properties: {
        SrcImage: `docker://${props.srcImage}`,
        DestImage: `docker://${props.dockerRepo.repositoryUri}:default`,
        RepositoryName: `${props.dockerRepo.repositoryName}`,
      },
    });
    this.customJob.node.addDependency(this.ecrDeployment);
  }

}