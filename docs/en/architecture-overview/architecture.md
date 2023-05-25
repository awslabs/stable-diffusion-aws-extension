The overall architecture of the extension is composed of two components: the extension and the middleware. The extension is a WebUI extension that is installed on the community WebUI and responsible for providing a user interface for users to interact with the middleware. The middleware is a set of AWS resources that are deployed on the user's AWS account and responsible for providing RESTful APIs for the extension to interact with AWS resources. The whole solution provide a seamless experience for users to train and deploy models on AWS with following features:

-   **User Experience**: Exising working flow is not changed, user can still use the community WebUI to train and deploy models with third-party extensions.
-   **Scalability**: Existing workload including training and inference can be easily scaled and accelerated on AWS SageMaker.
-   **Community**: Provided extension is part of the community WebUI, which is open source and keeps evolving with the community.

