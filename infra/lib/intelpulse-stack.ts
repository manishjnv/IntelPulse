import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class IntelPulseStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Tag all resources in this stack
    cdk.Tags.of(this).add('Project', 'IntelPulse');
    cdk.Tags.of(this).add('Environment', 'production');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');

    // Infrastructure components will be added in subsequent tasks
    // Task 2: VPC and networking
    // Task 3: EC2 for TimescaleDB
    // Task 4: ElastiCache Redis and OpenSearch
    // Task 5: ECR repositories
    // Task 6: ECS Fargate cluster and services
  }
}
