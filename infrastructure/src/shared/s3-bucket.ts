import { aws_s3, RemovalPolicy } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { BlockPublicAccess } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';


export class S3BucketStore {
  public readonly s3Bucket: aws_s3.Bucket;

  constructor(scope: Construct, id: string) {
    // Define the CORS configuration
    const corsRules: s3.CorsRule[] = [
      {
        allowedHeaders: ['*'],
        allowedMethods: [s3.HttpMethods.PUT, s3.HttpMethods.HEAD, s3.HttpMethods.GET],
        allowedOrigins: ['*'],
        exposedHeaders: ['ETag'],
      },
    ];

    //The code that defines your stack goes here
    this.s3Bucket = new s3.Bucket(scope, `${id}-aigc-bucket`, {
      blockPublicAccess: BlockPublicAccess.BLOCK_ACLS,
      removalPolicy: RemovalPolicy.RETAIN,
      cors: corsRules,
    });
  }
}