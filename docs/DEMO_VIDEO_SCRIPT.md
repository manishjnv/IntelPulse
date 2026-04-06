# Demo Video Script — IntelPulse (5 minutes)

## Recording Tips

- Use OBS Studio or Loom
- Resolution: 1920x1080
- Show browser + KIRO IDE side by side where relevant
- Speak clearly, keep pace steady

---

## 0:00-0:30 — Introduction

**Show**: IntelPulse dashboard at <https://intelpulse.tech>

"IntelPulse is a production-grade threat intelligence platform built for SOC analysts. It aggregates IOCs from 13+ external threat feeds, enriches them with AI using Amazon Bedrock, and provides searchable, actionable intelligence. This was built using KIRO IDE, Amazon Q Developer, and Amazon Bedrock as part of the AWS Codeathon Theme 3 — Intelligent Multi-Agent Domain Solutions."

---

## 0:30-1:30 — Dashboard & Core Features

**Show**: Navigate through dashboard

1. **Dashboard** — "The dashboard shows 3,029 intel items across 7 sources, with severity distribution, top risks, and feed health. All data is real, fetched from live threat intelligence feeds."

2. **Cyber News** — "19 RSS news sources are aggregated and AI-enriched using Amazon Bedrock Nova Lite. Each article gets structured intelligence — threat actors, CVEs, MITRE techniques, risk scores."
   - Click into an enriched article to show AI-generated fields

3. **Intel Items / Threat Feed** — "1,557 CISA KEV vulnerabilities, 500 URLhaus malicious URLs, 498 ThreatFox IOCs, and more — all scored and categorized."

---

## 1:30-2:30 — AI Enrichment with Amazon Bedrock

**Show**: News article detail with AI enrichment

"Amazon Bedrock Nova Lite powers our AI enrichment pipeline. When news articles are ingested, Bedrock analyzes the content and extracts structured intelligence."

- Show enriched fields: summary, executive brief, risk assessment, CVEs, MITRE techniques
- Show AI-generated reports page — click into the Weekly Summary report
- "Reports are generated using Bedrock with structured sections — executive summary, key findings, recommendations."

**Show**: IOC Database with IPinfo enrichment
"We also enrich IP IOCs with real geolocation data from IPinfo — 98 IPs enriched across 15+ countries."

---

## 2:30-3:30 — MITRE ATT&CK & Detection Rules

**Show**: MITRE ATT&CK page

"803 MITRE ATT&CK techniques are mapped to our intel items with 660 automated links. This gives SOC analysts immediate visibility into which techniques are being used in the wild."

**Show**: Detection Rules page
"We auto-generate detection rules — YARA, KQL, and Sigma — from our threat intelligence. These can be exported directly into SIEM and EDR tools."

**Show**: Geo View
"Geographic threat distribution shows real IPinfo-enriched data across countries and continents."

---

## 3:30-4:30 — KIRO IDE & Amazon Q Developer

**Show**: KIRO IDE with the project open

1. **Specs** — Open `.kiro/specs/aws-infrastructure-migration/design.md`
   "KIRO specs drove our entire development process. This 1,300-line design document was generated from requirements and guided all implementation."

2. **Steering** — Show `.kiro/steering/` files
   "Four steering files provided persistent context — tech stack, product info, coding standards, and AWS migration rules."

3. **Hooks** — Show `.kiro/hooks/`
   "Three hooks automated security scanning, documentation updates, and test synchronization."

4. **CDK Stack** — Show `infra/lib/intelpulse-stack.ts`
   "The entire AWS infrastructure — VPC, ECS Fargate, ALB, ElastiCache, OpenSearch, Bedrock agents — was generated using KIRO autopilot from the spec."

---

## 4:30-5:00 — Summary & Impact

**Show**: Dashboard one more time

"IntelPulse demonstrates how KIRO, Amazon Q Developer, and Amazon Bedrock work together to build a production-grade application. Key metrics:

- 76% time savings using KIRO + Q vs traditional development
- 3,029 real threat intel items from 12 live feeds
- AI enrichment powered by Amazon Bedrock Nova Lite
- Full AWS infrastructure defined in CDK
- 803 MITRE ATT&CK techniques mapped
- 2,500 IOCs with real geo enrichment

Thank you for reviewing IntelPulse."
