import {PythonLayerVersion} from '@aws-cdk/aws-lambda-python-alpha';
import {aws_dynamodb, StackProps} from 'aws-cdk-lib';
import {Resource} from 'aws-cdk-lib/aws-apigateway/lib/resource';
import * as s3 from 'aws-cdk-lib/aws-s3';
import {Construct} from 'constructs';
import {ResourceProvider} from './resource-provider';
import {CreateSchemaApi} from "../api/schemas/create-schema";
import {ListSchemasApi} from "../api/schemas/list-schemas";
import {DeleteSchemasApi} from "../api/schemas/delete-schemas";
import {GetSchemaApi} from "../api/schemas/get-schema";
import {UpdateSchemaApi} from "../api/schemas/update-schema";

export interface SchemaProps extends StackProps {
    routers: { [key: string]: Resource };
    s3_bucket: s3.Bucket;
    workflowsSchemasTable: aws_dynamodb.Table;
    multiUserTable: aws_dynamodb.Table;
    commonLayer: PythonLayerVersion;
    resourceProvider: ResourceProvider;
}

export class Schema {

    constructor(
        scope: Construct,
        props: SchemaProps,
    ) {

        new CreateSchemaApi(
            scope, 'CreateSchema', {
                workflowsSchemasTable: props.workflowsSchemasTable,
                commonLayer: props.commonLayer,
                httpMethod: 'POST',
                router: props.routers.schemas,
                multiUserTable: props.multiUserTable,
            },
        );


        new ListSchemasApi(
            scope, 'ListSchemas',
            {
                workflowsSchemasTable: props.workflowsSchemasTable,
                commonLayer: props.commonLayer,
                multiUserTable: props.multiUserTable,
                httpMethod: 'GET',
                router: props.routers.schemas,
            },
        );

        new DeleteSchemasApi(
            scope, 'DeleteSchemas',
            {
                workflowsSchemasTable: props.workflowsSchemasTable,
                commonLayer: props.commonLayer,
                httpMethod: 'DELETE',
                router: props.routers.schemas,
            },
        );

        const schemaResource = props.routers.schemas.addResource('{name}');

        new GetSchemaApi(
            scope, 'GetSchema',
            {
                workflowsSchemasTable: props.workflowsSchemasTable,
                commonLayer: props.commonLayer,
                multiUserTable: props.multiUserTable,
                httpMethod: 'GET',
                router: schemaResource,
            },
        );

        new UpdateSchemaApi(
            scope, 'UpdateSchema',
            {
                workflowsSchemasTable: props.workflowsSchemasTable,
                commonLayer: props.commonLayer,
                multiUserTable: props.multiUserTable,
                httpMethod: 'PUT',
                router: schemaResource,
            },
        );

    }

}
