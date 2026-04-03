"""Demo API endpoint for AI threat analysis.

Simplified endpoint for AWS Codethon demo - no agents, no complex infrastructure.
Just direct Bedrock SDK integration for IOC analysis.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.bedrock_adapter import get_bedrock_adapter

logger = get_logger(__name__)
router = APIRouter(prefix="/demo", tags=["demo"])


class ThreatAnalysisRequest(BaseModel):
    """Request model for threat analysis."""
    
    ioc: str = Field(..., description="Indicator of Compromise (IP, domain, or hash)")
    ioc_type: str = Field(..., description="Type of IOC: ip, domain, or hash")


class ThreatAnalysisResponse(BaseModel):
    """Response model for threat analysis."""
    
    ioc: str
    ioc_type: str
    analysis: str
    risk_score: int | None = None
    severity: str | None = None
    confidence: int | None = None
    mitre_techniques: list[str] = []
    recommended_actions: list[str] = []


@router.post("/analyze", response_model=ThreatAnalysisResponse)
async def analyze_threat(request: ThreatAnalysisRequest):
    """Analyze a threat indicator using Amazon Bedrock.
    
    This is a simplified demo endpoint that uses direct Bedrock SDK calls
    without agents or action groups. Perfect for demonstrating AI integration.
    
    Args:
        request: IOC and type to analyze
        
    Returns:
        Comprehensive threat analysis with risk scoring
        
    Example:
        ```
        POST /api/v1/demo/analyze
        {
            "ioc": "1.2.3.4",
            "ioc_type": "ip"
        }
        ```
    """
    logger.info(
        "demo_threat_analysis_request",
        ioc=request.ioc,
        ioc_type=request.ioc_type,
    )
    
    try:
        # Get Bedrock adapter
        bedrock = get_bedrock_adapter()
        
        # Build analysis prompt
        system_prompt = """You are a cybersecurity threat analyst specializing in IOC (Indicator of Compromise) analysis.

Your task is to analyze the given IOC and provide a comprehensive threat assessment.

For each IOC, provide:
1. Risk assessment and potential threats
2. Common attack patterns associated with this type of IOC
3. MITRE ATT&CK techniques that might be relevant
4. Recommended security actions

Be specific, actionable, and security-focused."""

        user_prompt = f"""Analyze this Indicator of Compromise:

IOC: {request.ioc}
Type: {request.ioc_type}

Provide a comprehensive threat analysis including:
- What this IOC might indicate
- Potential threat level (assign a risk score 0-100)
- Severity level (CRITICAL, HIGH, MEDIUM, LOW, or INFO)
- Confidence in the assessment (0-100%)
- Relevant MITRE ATT&CK techniques (list technique IDs like T1566)
- Recommended actions for security teams

Format your response as a clear, structured analysis."""

        # Call Bedrock
        analysis_text = await bedrock.ai_analyze(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1000,
            temperature=0.3,
        )
        
        if not analysis_text:
            raise HTTPException(
                status_code=500,
                detail="Failed to get analysis from Bedrock"
            )
        
        # Parse structured data from response (simple extraction)
        risk_score = _extract_risk_score(analysis_text)
        severity = _extract_severity(analysis_text)
        confidence = _extract_confidence(analysis_text)
        mitre_techniques = _extract_mitre_techniques(analysis_text)
        recommended_actions = _extract_actions(analysis_text)
        
        logger.info(
            "demo_threat_analysis_success",
            ioc=request.ioc,
            risk_score=risk_score,
            severity=severity,
        )
        
        return ThreatAnalysisResponse(
            ioc=request.ioc,
            ioc_type=request.ioc_type,
            analysis=analysis_text,
            risk_score=risk_score,
            severity=severity,
            confidence=confidence,
            mitre_techniques=mitre_techniques,
            recommended_actions=recommended_actions,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "demo_threat_analysis_error",
            error=str(e),
            error_type=type(e).__name__,
            ioc=request.ioc,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


def _extract_risk_score(text: str) -> int | None:
    """Extract risk score from analysis text."""
    import re
    
    # Look for patterns like "risk score: 85" or "score of 75"
    patterns = [
        r'risk score[:\s]+(\d+)',
        r'score[:\s]+(\d+)',
        r'(\d+)/100',
        r'(\d+)\s*out of 100',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    
    return None


def _extract_severity(text: str) -> str | None:
    """Extract severity level from analysis text."""
    import re
    
    # Look for severity keywords
    severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
    
    for severity in severities:
        if re.search(rf'\b{severity}\b', text, re.IGNORECASE):
            return severity
    
    return None


def _extract_confidence(text: str) -> int | None:
    """Extract confidence percentage from analysis text."""
    import re
    
    # Look for patterns like "confidence: 85%" or "85% confident"
    patterns = [
        r'confidence[:\s]+(\d+)%',
        r'(\d+)%\s+confiden',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            conf = int(match.group(1))
            if 0 <= conf <= 100:
                return conf
    
    return None


def _extract_mitre_techniques(text: str) -> list[str]:
    """Extract MITRE ATT&CK technique IDs from analysis text."""
    import re
    
    # Look for patterns like T1566, T1059.001
    pattern = r'\bT\d{4}(?:\.\d{3})?\b'
    matches = re.findall(pattern, text)
    
    # Return unique techniques
    return list(set(matches))


def _extract_actions(text: str) -> list[str]:
    """Extract recommended actions from analysis text."""
    import re
    
    # Look for bullet points or numbered lists
    lines = text.split('\n')
    actions = []
    
    for line in lines:
        line = line.strip()
        # Match lines starting with -, *, •, or numbers
        if re.match(r'^[-*•]\s+', line) or re.match(r'^\d+\.\s+', line):
            # Clean up the action text
            action = re.sub(r'^[-*•\d.]+\s+', '', line)
            if action and len(action) > 10:  # Ignore very short items
                actions.append(action)
    
    return actions[:5]  # Return top 5 actions


@router.get("/health")
async def demo_health():
    """Check if demo endpoint and Bedrock are working."""
    try:
        bedrock = get_bedrock_adapter()
        health = await bedrock.check_health()
        
        return {
            "status": "healthy" if health.get("healthy") else "unhealthy",
            "bedrock": health,
            "demo_endpoint": "operational",
        }
    except Exception as e:
        logger.error("demo_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "demo_endpoint": "operational",
        }
