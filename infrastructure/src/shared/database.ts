import {Construct} from 'constructs';
import {ResourceProvider} from './resource-provider';
import {Table} from 'aws-cdk-lib/aws-dynamodb';


export class Database {

    public modelTable: Table;
    public trainingTable: Table;
    public checkpointTable: Table;
    public datasetInfoTable: Table;
    public datasetItemTable: Table;
    public sDInferenceJobTable: Table;
    public sDEndpointDeploymentJobTable: Table;
    public multiUserTable: Table;

    constructor(scope: Construct, baseId: string, resourceProvider: ResourceProvider) {

        this.modelTable = this.table(scope, baseId, 'ModelTable');
        this.modelTable.node.addDependency(resourceProvider.resources);

        this.trainingTable = this.table(scope, baseId, 'TrainingTable');
        this.trainingTable.node.addDependency(resourceProvider.resources);


        this.checkpointTable = this.table(scope, baseId, 'CheckpointTable');
        this.checkpointTable.node.addDependency(resourceProvider.resources);


        this.datasetInfoTable = this.table(scope, baseId, 'DatasetInfoTable');
        this.datasetInfoTable.node.addDependency(resourceProvider.resources);


        this.datasetItemTable = this.table(scope, baseId, 'DatasetItemTable');
        this.datasetItemTable.node.addDependency(resourceProvider.resources);


        this.sDInferenceJobTable = this.table(scope, baseId, 'SDInferenceJobTable');
        this.sDInferenceJobTable.node.addDependency(resourceProvider.resources);


        this.sDEndpointDeploymentJobTable = this.table(scope, baseId, 'SDEndpointDeploymentJobTable');
        this.sDEndpointDeploymentJobTable.node.addDependency(resourceProvider.resources);


        this.multiUserTable = this.table(scope, baseId, 'MultiUserTable');
        this.multiUserTable.node.addDependency(resourceProvider.resources);

    }

    private table(scope: Construct, baseId: string, tableName: string): Table {
        return <Table>Table.fromTableName(scope, `${baseId}-${tableName}`, tableName);
    }
}
