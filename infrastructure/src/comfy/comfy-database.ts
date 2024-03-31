import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class ComfyDatabase extends Construct {
  public templateTable: Table;
  public configTable: Table;
  public executeTable: Table;
  public syncTable: Table;
  public msgTable: Table;
  public instanceMonitorTable: Table;

  constructor(scope: Construct, baseId: string) {
    super(scope, baseId);
    this.templateTable = this.table(scope, baseId, 'ComfyTemplateTable');

    this.configTable = this.table(scope, baseId, 'ComfyConfigTable');

    this.executeTable = this.table(scope, baseId, 'ComfyExecuteTable');

    this.syncTable = this.table(scope, baseId, 'ComfySyncTable');

    this.instanceMonitorTable = this.table(scope, baseId, 'ComfyInstanceMonitorTable');

    this.msgTable = this.table(scope, baseId, 'ComfyMessageTable');

  }

  private table(scope: Construct, baseId: string, tableName: string): Table {
    return <Table>Table.fromTableName(scope, `${baseId}-${tableName}`, tableName);
  }
}