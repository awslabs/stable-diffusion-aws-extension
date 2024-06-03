import {PythonLayerVersion} from '@aws-cdk/aws-lambda-python-alpha';
import {aws_dynamodb, StackProps} from 'aws-cdk-lib';
import {Resource} from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3 from 'aws-cdk-lib/aws-s3';
import {Construct} from 'constructs';
import {ResourceProvider} from './resource-provider';
import {CreateWorkflowApi} from "../api/workflows/create-workflow";
import {ListWorkflowsApi} from "../api/workflows/list-workflows";
import {DeleteWorkflowsApi} from "../api/workflows/delete-workflows";
import {GetWorkflowApi} from "../api/workflows/get-workflow";

export interface WorkflowProps extends StackProps {
    routers: { [key: string]: Resource };
    s3_bucket: s3.Bucket;
    workflowsTable: aws_dynamodb.Table;
    multiUserTable: aws_dynamodb.Table;
    commonLayer: PythonLayerVersion;
    resourceProvider: ResourceProvider;
}

export class Workflow {

    constructor(
        scope: Construct,
        props: WorkflowProps,
    ) {

        new CreateWorkflowApi(
            scope, 'CreateWorkflow', {
                workflowsTable: props.workflowsTable,
                commonLayer: props.commonLayer,
                httpMethod: 'POST',
                router: props.routers.workflows,
                multiUserTable: props.multiUserTable,
            },
        );


        new ListWorkflowsApi(
            scope, 'ListWorkflowsJobs',
            {
                workflowsTable: props.workflowsTable,
                commonLayer: props.commonLayer,
                multiUserTable: props.multiUserTable,
                httpMethod: 'GET',
                router: props.routers.workflows,
            },
        );

        new DeleteWorkflowsApi(
            scope, 'DeleteWorkflows',
            {
                workflowsTable: props.workflowsTable,
                commonLayer: props.commonLayer,
                multiUserTable: props.multiUserTable,
                httpMethod: 'DELETE',
                router: props.routers.workflows,
            },
        );

        new GetWorkflowApi(
            scope, 'GetWorkflow',
            {
                workflowsTable: props.workflowsTable,
                commonLayer: props.commonLayer,
                multiUserTable: props.multiUserTable,
                httpMethod: 'GET',
                router: props.routers.workflows,
            },
        );


    }

}
