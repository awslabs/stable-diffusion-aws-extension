import { App, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import { SdTrainDeployStack } from "./sd-train/sd-train-deploy-stack";
import { SDAsyncInferenceStackProps,SDAsyncInferenceStack } from "./sd-inference/sd-async-inference-stack";
import {
    BootstraplessStackSynthesizer,
    CompositeECRRepositoryAspect,
} from "cdk-bootstrapless-synthesizer";
import { Aspects } from "aws-cdk-lib";

// for development, use account/region from cdk cli
const devEnv = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
};

const app = new App();

export class Middleware extends Stack {
    constructor(
        scope: Construct,
        id: string,
        props: StackProps = {
            env: devEnv,
            synthesizer: synthesizer(),
        }
    ) {
        super(scope, id, props);

        const trainStack = new SdTrainDeployStack(this, "SdDreamBoothTrainStack", {
            env: devEnv,
            synthesizer: synthesizer()
        });

        const inferenceStack = new SDAsyncInferenceStack(
            this,
            "SdAsyncInferenceStack-dev",
            <SDAsyncInferenceStackProps>{
                env: devEnv,
                api_gate_way: trainStack.apiGateway,
                s3_bucket: trainStack.s3Bucket,
                training_table: trainStack.trainingTable,
                snsTopic: trainStack.snsTopic,
                synthesizer: synthesizer(),
                default_endpoint_name: trainStack.default_endpoint_name
            }
        );

        inferenceStack.addDependency(trainStack);
    }
}

new Middleware(
    app,
    "Stable-diffusion-aws-extension-middleware-stack",
    {
        env: devEnv,
        synthesizer: synthesizer(),
    }
);

app.synth();
// below lines are required if your application has Docker assets
if (process.env.USE_BSS) {
    Aspects.of(app).add(new CompositeECRRepositoryAspect());
}

function synthesizer() {
    return process.env.USE_BSS
        ? new BootstraplessStackSynthesizer()
        : undefined;
}
