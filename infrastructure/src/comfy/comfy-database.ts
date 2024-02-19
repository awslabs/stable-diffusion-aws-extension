import { Table } from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class ComfyDatabase extends Construct {
  public templateTable: Table;
  public configTable: Table;
  public executeTable: Table;
  public nodeTable: Table;
  public msgTable: Table;

  constructor(scope: Construct, baseId: string) {
    super(scope, baseId);
    this.templateTable = this.table(scope, baseId, 'ComfyTemplateTable');

    this.configTable = this.table(scope, baseId, 'ComfyConfigTable');

    this.executeTable = this.table(scope, baseId, 'ComfyExecuteTable');

    this.nodeTable = this.table(scope, baseId, 'ComfyNodeTable');

    this.msgTable = this.table(scope, baseId, 'ComfyMessageTable');

  }

  private table(scope: Construct, baseId: string, tableName: string): Table {
    return <Table>Table.fromTableName(scope, `${baseId}-${tableName}`, tableName);
  }
}