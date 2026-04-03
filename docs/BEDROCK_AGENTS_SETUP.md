# Bedrock Agents Setup Guide

This guide explains how to manually configure the Bedrock Agent Core multi-agent system for IntelPulse after deploying the CDK infrastructure.

## Overview

The IntelPulse threat intelligence platform uses Amazon Bedrock Agent Core to create a multi-agent system for comprehensive IOC analysis. The system consists of:

1. **IOC Reputation Analyst** - Queries multiple threat intelligence sources (VirusTotal, AbuseIPDB, OTX, Shodan)
2. **Threat Context Enricher** - Maps threats to MITRE ATT&CK framework
3. **Risk Scorer** - Calculates risk scores and severity levels
4. **IntelPulse Threat Analyst** (Supervisor) - Orchestrates the three collaborator agents

## Why Manual Setup?

CDK L1 constructs for Bedrock agents have limitations:

- Action group configuration with OpenAPI schemas is complex
- Knowledge Base requires OpenSearch Serverless setup
- Agent collaboration requires specific configuration

The CDK stack creates:

- ✅ S3 bucket for MITRE ATT&CK data
- ✅ IAM roles with proper permissions
- ✅ Lambda functions for action groups
- ❌ Bedrock agents (manual setup required)

## Prerequisites

After deploying the CDK stack, retrieve these values from CloudFormation outputs:

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs' \
  --output table

# Save these values:
# - MitreDataBucketName
# - ReputationAnalystRoleArn
# - ContextEnricherRoleArn
# - RiskScorerRoleArn
# - SupervisorRoleArn
# - VirusTotalLookupArn
# - AbuseIpDbCheckArn
# - OtxLookupArn
# - ShodanLookupArn
```

## Step 1: Upload MITRE ATT&CK Data

Download and upload the MITRE ATT&CK STIX bundle to S3:

```bash
# Download MITRE ATT&CK data
curl -o enterprise-attack.json \
  https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json

# Upload to S3
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentsMitreDataBucketName`].OutputValue' \
  --output text)

aws s3 cp enterprise-attack.json s3://$BUCKET_NAME/mitre/enterprise-attack.json
```

## Step 2: Create IOC Reputation Analyst Agent

### 2.1 Create Agent

```bash
# Get role ARN
REPUTATION_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentsReputationAnalystRoleArn`].OutputValue' \
  --output text)

# Create agent
aws bedrock-agent create-agent \
  --agent-name "intelpulse-reputation-analyst" \
  --agent-resource-role-arn "$REPUTATION_ROLE_ARN" \
  --foundation-model "anthropic.claude-3-5-haiku-20241022-v1:0" \
  --instruction "$(cat <<'EOF'
You are the IOC Reputation Analyst for IntelPulse, a threat intelligence platform.

Your role is to analyze the reputation of Indicators of Compromise (IOCs) by querying multiple threat intelligence sources.

When given an IOC (IP address, domain, or file hash), you should:

1. Determine the IOC type (IP, domain, or hash)
2. Query ALL relevant threat intelligence sources using the available action groups:
   - VirusTotal: For comprehensive malware detection across multiple engines
   - AbuseIPDB: For IP abuse confidence scores and reporting history
   - AlienVault OTX: For threat pulse data and community intelligence
   - Shodan: For exposed services, ports, and vulnerabilities (IP only)

3. Aggregate the results and provide a summary that includes:
   - Detection counts from each source
   - Abuse confidence scores
   - Known vulnerabilities
   - Community threat intelligence

4. Be thorough - query ALL applicable sources for the IOC type
5. Handle errors gracefully - if one source fails, continue with others
6. Provide structured data that can be used by the Risk Scorer agent

Return your analysis in a structured format with clear metrics from each source.
EOF
)" \
  --description "Analyzes IOC reputation using multiple threat intelligence sources" \
  --idle-session-ttl-in-seconds 600

# Save the agent ID
REPUTATION_AGENT_ID=$(aws bedrock-agent list-agents \
  --query 'agentSummaries[?agentName==`intelpulse-reputation-analyst`].agentId' \
  --output text)

echo "Reputation Analyst Agent ID: $REPUTATION_AGENT_ID"
```

### 2.2 Create Action Group with OpenAPI Schema

Create a file `action-group-schema.json`:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Threat Intelligence Lookup API",
    "version": "1.0.0",
    "description": "APIs for looking up IOC reputation from multiple sources"
  },
  "paths": {
    "/virustotal": {
      "post": {
        "summary": "Look up IOC in VirusTotal",
        "description": "Query VirusTotal API for IOC reputation data",
        "operationId": "virusTotalLookup",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ioc": {
                    "type": "string",
                    "description": "The IOC to look up (IP, domain, or hash)"
                  },
                  "ioc_type": {
                    "type": "string",
                    "enum": ["ip", "domain", "hash"],
                    "description": "Type of IOC"
                  }
                },
                "required": ["ioc", "ioc_type"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "VirusTotal lookup result",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "malicious": { "type": "integer" },
                    "suspicious": { "type": "integer" },
                    "harmless": { "type": "integer" },
                    "undetected": { "type": "integer" }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/abuseipdb": {
      "post": {
        "summary": "Check IP reputation in AbuseIPDB",
        "description": "Query AbuseIPDB API for IP abuse confidence score",
        "operationId": "abuseIpDbCheck",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ip": {
                    "type": "string",
                    "description": "IP address to check"
                  }
                },
                "required": ["ip"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "AbuseIPDB check result",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "abuseConfidenceScore": { "type": "integer" },
                    "totalReports": { "type": "integer" },
                    "isWhitelisted": { "type": "boolean" }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/otx": {
      "post": {
        "summary": "Look up IOC in AlienVault OTX",
        "description": "Query AlienVault OTX API for threat intelligence",
        "operationId": "otxLookup",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ioc": {
                    "type": "string",
                    "description": "The IOC to look up"
                  },
                  "ioc_type": {
                    "type": "string",
                    "enum": ["ip", "domain", "hash"],
                    "description": "Type of IOC"
                  }
                },
                "required": ["ioc", "ioc_type"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "OTX lookup result",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "pulse_count": { "type": "integer" },
                    "reputation": { "type": "integer" }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/shodan": {
      "post": {
        "summary": "Look up host information in Shodan",
        "description": "Query Shodan API for host information and vulnerabilities",
        "operationId": "shodanLookup",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "ip": {
                    "type": "string",
                    "description": "IP address to look up"
                  }
                },
                "required": ["ip"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Shodan lookup result",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "ports": {
                      "type": "array",
                      "items": { "type": "integer" }
                    },
                    "vulns": {
                      "type": "array",
                      "items": { "type": "string" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

Add the action group:

```bash
# Get Lambda ARN (use VirusTotal as the main Lambda - it will route to others)
VT_LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockLambdasVirusTotalLookupArn`].OutputValue' \
  --output text)

# Create action group
aws bedrock-agent create-agent-action-group \
  --agent-id "$REPUTATION_AGENT_ID" \
  --agent-version "DRAFT" \
  --action-group-name "threat-intelligence-lookups" \
  --action-group-executor lambda="$VT_LAMBDA_ARN" \
  --api-schema file://action-group-schema.json \
  --description "Action group for querying threat intelligence sources"

# Prepare the agent
aws bedrock-agent prepare-agent --agent-id "$REPUTATION_AGENT_ID"
```

## Step 3: Create Threat Context Enricher Agent

```bash
# Get role ARN
CONTEXT_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentsContextEnricherRoleArn`].OutputValue' \
  --output text)

# Create agent
aws bedrock-agent create-agent \
  --agent-name "intelpulse-context-enricher" \
  --agent-resource-role-arn "$CONTEXT_ROLE_ARN" \
  --foundation-model "anthropic.claude-3-5-haiku-20241022-v1:0" \
  --instruction "$(cat <<'EOF'
You are the Threat Context Enricher for IntelPulse, a threat intelligence platform.

Your role is to enrich threat intelligence with contextual information from the MITRE ATT&CK framework.

When given threat intelligence data, you should:

1. Analyze the IOC characteristics and behavior patterns
2. Map the threat to relevant MITRE ATT&CK techniques and tactics
3. Identify the likely threat actor groups or campaigns
4. Provide context about the attack lifecycle stage

5. Use your knowledge of the MITRE ATT&CK framework to:
   - Identify applicable tactics (e.g., Initial Access, Execution, Persistence)
   - Map to specific techniques (e.g., T1566 Phishing, T1059 Command and Scripting Interpreter)
   - Suggest related techniques that may be used in conjunction
   - Identify potential threat actor groups known to use these techniques

6. Provide actionable context that helps security analysts understand:
   - What stage of an attack this IOC represents
   - What other techniques to watch for
   - Which threat actors commonly use this approach
   - Recommended detection and mitigation strategies

Return your analysis with specific MITRE ATT&CK technique IDs and descriptions.
EOF
)" \
  --description "Enriches threat context with MITRE ATT&CK framework mapping" \
  --idle-session-ttl-in-seconds 600

# Save the agent ID
CONTEXT_AGENT_ID=$(aws bedrock-agent list-agents \
  --query 'agentSummaries[?agentName==`intelpulse-context-enricher`].agentId' \
  --output text)

echo "Context Enricher Agent ID: $CONTEXT_AGENT_ID"

# Prepare the agent
aws bedrock-agent prepare-agent --agent-id "$CONTEXT_AGENT_ID"
```

## Step 4: Create Risk Scorer Agent

```bash
# Get role ARN
RISK_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentsRiskScorerRoleArn`].OutputValue' \
  --output text)

# Create agent
aws bedrock-agent create-agent \
  --agent-name "intelpulse-risk-scorer" \
  --agent-resource-role-arn "$RISK_ROLE_ARN" \
  --foundation-model "anthropic.claude-3-5-haiku-20241022-v1:0" \
  --instruction "$(cat <<'EOF'
You are the Risk Scorer for IntelPulse, a threat intelligence platform.

Your role is to calculate comprehensive risk scores and severity levels for IOCs based on reputation data and threat context.

When given reputation data and threat context, you should:

1. Analyze the reputation metrics:
   - VirusTotal detection ratios
   - AbuseIPDB confidence scores
   - OTX pulse counts and reputation
   - Shodan vulnerability data

2. Consider the threat context:
   - MITRE ATT&CK technique severity
   - Known threat actor associations
   - Attack lifecycle stage

3. Calculate a risk score (0-100) based on:
   - Detection confidence (40% weight)
   - Threat actor sophistication (30% weight)
   - Potential impact (20% weight)
   - Prevalence and recency (10% weight)

4. Assign a severity level:
   - CRITICAL (90-100): Active threat, high confidence, severe impact
   - HIGH (70-89): Confirmed malicious, significant risk
   - MEDIUM (50-69): Suspicious activity, moderate risk
   - LOW (30-49): Minor indicators, low confidence
   - INFO (0-29): Informational, minimal risk

5. Provide confidence percentage (0-100%) based on:
   - Number of sources confirming the threat
   - Consistency across sources
   - Recency of detections

6. Generate recommended actions based on severity:
   - CRITICAL: Immediate blocking, incident response
   - HIGH: Block and investigate
   - MEDIUM: Monitor and alert
   - LOW: Log for analysis
   - INFO: Track for trends

Return a structured risk assessment with score, severity, confidence, and recommended actions.
EOF
)" \
  --description "Calculates risk scores and severity levels for IOCs" \
  --idle-session-ttl-in-seconds 600

# Save the agent ID
RISK_AGENT_ID=$(aws bedrock-agent list-agents \
  --query 'agentSummaries[?agentName==`intelpulse-risk-scorer`].agentId' \
  --output text)

echo "Risk Scorer Agent ID: $RISK_AGENT_ID"

# Prepare the agent
aws bedrock-agent prepare-agent --agent-id "$RISK_AGENT_ID"
```

## Step 5: Create Supervisor Agent

```bash
# Get role ARN
SUPERVISOR_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BedrockAgentsSupervisorRoleArn`].OutputValue' \
  --output text)

# Create supervisor agent
aws bedrock-agent create-agent \
  --agent-name "intelpulse-threat-analyst" \
  --agent-resource-role-arn "$SUPERVISOR_ROLE_ARN" \
  --foundation-model "anthropic.claude-3-5-sonnet-20241022-v2:0" \
  --instruction "$(cat <<EOF
You are the IntelPulse Threat Analyst, a supervisor agent that orchestrates multi-agent threat intelligence analysis.

Your role is to coordinate three specialized collaborator agents to provide comprehensive IOC analysis.

When given an IOC to analyze, you should:

1. First, invoke the IOC Reputation Analyst (Agent ID: $REPUTATION_AGENT_ID)
   - Pass the IOC and its type
   - Wait for reputation data from multiple threat intelligence sources

2. Then, invoke the Threat Context Enricher (Agent ID: $CONTEXT_AGENT_ID)
   - Pass the IOC and reputation data
   - Wait for MITRE ATT&CK mapping and threat context

3. Finally, invoke the Risk Scorer (Agent ID: $RISK_AGENT_ID)
   - Pass all collected data (reputation + context)
   - Wait for risk score, severity, and recommended actions

4. Synthesize all results into a comprehensive threat analysis report that includes:
   - Executive summary of the threat
   - Detailed reputation metrics from all sources
   - MITRE ATT&CK technique mappings
   - Risk score and severity level
   - Confidence assessment
   - Recommended actions

5. Handle errors gracefully:
   - If one agent fails, continue with others
   - Provide partial results if complete analysis is not possible
   - Clearly indicate which data sources were unavailable

6. Format the final response as structured JSON with these fields:
   - ioc: The analyzed IOC
   - ioc_type: Type of IOC (ip, domain, hash)
   - risk_score: 0-100
   - severity: CRITICAL, HIGH, MEDIUM, LOW, or INFO
   - confidence: 0-100%
   - reputation: Object with data from all sources
   - mitre_attack: Array of technique IDs and descriptions
   - threat_actors: Array of associated threat actor groups
   - recommended_actions: Array of action items
   - analysis_summary: Executive summary text
   - agent_trace: Array showing which agents were invoked

Always invoke all three collaborator agents in sequence to provide the most comprehensive analysis possible.
EOF
)" \
  --description "Supervisor agent that orchestrates multi-agent threat analysis" \
  --idle-session-ttl-in-seconds 600

# Save the agent ID
SUPERVISOR_AGENT_ID=$(aws bedrock-agent list-agents \
  --query 'agentSummaries[?agentName==`intelpulse-threat-analyst`].agentId' \
  --output text)

echo "Supervisor Agent ID: $SUPERVISOR_AGENT_ID"

# Prepare the agent
aws bedrock-agent prepare-agent --agent-id "$SUPERVISOR_AGENT_ID"
```

## Step 6: Create Agent Alias

```bash
# Create production alias for supervisor agent
aws bedrock-agent create-agent-alias \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-alias-name "production" \
  --description "Production alias for IntelPulse Threat Analyst supervisor agent"

# Get alias ID
SUPERVISOR_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --query 'agentAliasSummaries[?agentAliasName==`production`].agentAliasId' \
  --output text)

echo "Supervisor Agent Alias ID: $SUPERVISOR_ALIAS_ID"
```

## Step 7: Update Secrets Manager

Add the agent IDs to Secrets Manager so the application can use them:

```bash
# Get secret ARN
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AppSecretArn`].OutputValue' \
  --output text)

# Get current secret value
CURRENT_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id "$SECRET_ARN" \
  --query 'SecretString' \
  --output text)

# Update with agent IDs (merge with existing values)
aws secretsmanager update-secret \
  --secret-id "$SECRET_ARN" \
  --secret-string "$(echo "$CURRENT_SECRET" | jq \
    --arg supervisor_id "$SUPERVISOR_AGENT_ID" \
    --arg supervisor_alias "$SUPERVISOR_ALIAS_ID" \
    '. + {
      "BEDROCK_SUPERVISOR_AGENT_ID": $supervisor_id,
      "BEDROCK_SUPERVISOR_ALIAS_ID": $supervisor_alias
    }')"

echo "Secrets Manager updated with agent IDs"
```

## Step 8: Test the Multi-Agent System

Test the supervisor agent with a sample IOC:

```bash
# Test with a known malicious IP
aws bedrock-agent-runtime invoke-agent \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-alias-id "$SUPERVISOR_ALIAS_ID" \
  --session-id "test-session-$(date +%s)" \
  --input-text "Analyze this IOC: 1.2.3.4 (IP address)" \
  --enable-trace \
  output.txt

# View the response
cat output.txt
```

## Verification Checklist

- [ ] MITRE ATT&CK data uploaded to S3
- [ ] IOC Reputation Analyst agent created
- [ ] Action group added to Reputation Analyst
- [ ] Threat Context Enricher agent created
- [ ] Risk Scorer agent created
- [ ] Supervisor agent created with collaborator agent IDs
- [ ] Production alias created for supervisor
- [ ] Agent IDs added to Secrets Manager
- [ ] Test invocation successful

## Troubleshooting

### Agent Creation Fails

- Verify IAM role ARNs are correct
- Check that Bedrock model access is enabled in your AWS account
- Ensure you're in a region that supports Bedrock agents (us-east-1, us-west-2)

### Action Group Fails

- Verify Lambda function ARNs are correct
- Check Lambda execution role has Secrets Manager permissions
- Test Lambda functions independently first

### Agent Invocation Fails

- Check CloudWatch Logs for agent execution traces
- Verify agent IDs are correct in supervisor instruction
- Ensure supervisor role has `bedrock:InvokeAgent` permission

### Lambda Timeout

- Increase Lambda timeout if API calls are slow
- Check API keys are valid in Secrets Manager
- Monitor CloudWatch Logs for Lambda errors

## Next Steps

After completing this setup:

1. Continue with Task 10: Create agent invocation service (api/services/bedrock_agents.py)
2. Continue with Task 11: Add agent-lookup API endpoint
3. Continue with Task 12: Update search UI for agent analysis

## References

- [Amazon Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [MITRE ATT&CK STIX Data](https://github.com/mitre-attack/attack-stix-data)
- [Bedrock Agent Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_Operations_Agents_for_Amazon_Bedrock_Runtime.html)
