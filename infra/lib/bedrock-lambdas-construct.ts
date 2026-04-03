/**
 * CDK Construct for Bedrock Agent Lambda action groups.
 * 
 * Creates 4 Lambda functions that serve as action groups for Bedrock agents:
 * - VirusTotal lookup
 * - AbuseIPDB check
 * - AlienVault OTX lookup
 * - Shodan lookup
 */

import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import * as path from 'path';

export interface BedrockLambdasConstructProps {
  /**
   * Secrets Manager secret containing API keys
   */
  appSecret: secretsmanager.ISecret;
}

export class BedrockLambdasConstruct extends Construct {
  public readonly virusTotalLookup: lambda.Function;
  public readonly abuseIpDbCheck: lambda.Function;
  public readonly otxLookup: lambda.Function;
  public readonly shodanLookup: lambda.Function;

  constructor(scope: Construct, id: string, props: BedrockLambdasConstructProps) {
    super(scope, id);

    // Create IAM role for Lambda functions
    const lambdaRole = new iam.Role(this, 'BedrockLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'IAM role for Bedrock agent Lambda functions',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // Grant permission to read secrets
    props.appSecret.grantRead(lambdaRole);

    // Common Lambda configuration
    const commonConfig = {
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      role: lambdaRole,
      environment: {
        SECRET_ARN: props.appSecret.secretArn,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    };

    // Create VirusTotal lookup Lambda
    this.virusTotalLookup = new lambda.Function(this, 'VirusTotalLookup', {
      ...commonConfig,
      functionName: 'intelpulse-virustotal-lookup',
      description: 'VirusTotal IOC lookup for Bedrock agent',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambdas/virustotal_lookup')),
      handler: 'handler.lambda_handler',
    });

    // Create AbuseIPDB check Lambda
    this.abuseIpDbCheck = new lambda.Function(this, 'AbuseIpDbCheck', {
      ...commonConfig,
      functionName: 'intelpulse-abuseipdb-check',
      description: 'AbuseIPDB IP reputation check for Bedrock agent',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambdas/abuseipdb_check')),
      handler: 'handler.lambda_handler',
    });

    // Create OTX lookup Lambda
    this.otxLookup = new lambda.Function(this, 'OtxLookup', {
      ...commonConfig,
      functionName: 'intelpulse-otx-lookup',
      description: 'AlienVault OTX threat intelligence lookup for Bedrock agent',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambdas/otx_lookup')),
      handler: 'handler.lambda_handler',
    });

    // Create Shodan lookup Lambda
    this.shodanLookup = new lambda.Function(this, 'ShodanLookup', {
      ...commonConfig,
      functionName: 'intelpulse-shodan-lookup',
      description: 'Shodan host information lookup for Bedrock agent',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambdas/shodan_lookup')),
      handler: 'handler.lambda_handler',
    });

    // Output Lambda ARNs
    new cdk.CfnOutput(this, 'VirusTotalLookupArn', {
      value: this.virusTotalLookup.functionArn,
      description: 'VirusTotal Lookup Lambda ARN',
      exportName: 'IntelPulse-VirusTotalLookupArn',
    });

    new cdk.CfnOutput(this, 'AbuseIpDbCheckArn', {
      value: this.abuseIpDbCheck.functionArn,
      description: 'AbuseIPDB Check Lambda ARN',
      exportName: 'IntelPulse-AbuseIpDbCheckArn',
    });

    new cdk.CfnOutput(this, 'OtxLookupArn', {
      value: this.otxLookup.functionArn,
      description: 'OTX Lookup Lambda ARN',
      exportName: 'IntelPulse-OtxLookupArn',
    });

    new cdk.CfnOutput(this, 'ShodanLookupArn', {
      value: this.shodanLookup.functionArn,
      description: 'Shodan Lookup Lambda ARN',
      exportName: 'IntelPulse-ShodanLookupArn',
    });
  }
}
