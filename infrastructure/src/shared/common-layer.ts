import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export class LambdaCommonLayer {

  public readonly commonLayer: PythonLayerVersion;

  constructor(scope: Construct, id: string) {

    this.commonLayer = new PythonLayerVersion(scope, `${id}-common-layer`, {
      entry: '../middleware_api',
      bundling: {
        outputPathSuffix: '/python',
      },
      compatibleRuntimes: [Runtime.PYTHON_3_10],
    });
  }
}
