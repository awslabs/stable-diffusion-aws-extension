import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';
import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export class LambdaCommonLayer {

  public readonly commonLayer: PythonLayerVersion;

  constructor(scope: Construct, id: string, srcRoot: string) {

    this.commonLayer = new PythonLayerVersion(scope, id, {
      entry: srcRoot,
      bundling: {
        outputPathSuffix: '/python',
        command: [
          'bash',
          '-c',
          [
            'cp -R /asset-input/common /asset-output/python/',
            'cp -R /asset-input/libs /asset-output/python/',
            'pip install -r requirements.txt -t /asset-output/python/',
          ].join(' && '),
        ],
        image: Runtime.PYTHON_3_9.bundlingImage,
      },
      compatibleRuntimes: [Runtime.PYTHON_3_9],
    });
  }
}
