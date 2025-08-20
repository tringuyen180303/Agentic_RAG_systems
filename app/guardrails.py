import re
import os
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
import hashlib
from dataclasses import dataclass
from langfuse import Langfuse
from dotenv import load_dotenv
import datetime
class GuardrailViolationType(Enum):
    SENSITIVE_DATA = "sensitive_data"
    COMPETITOR_MENTION = "competitor_mention"
    PII_DETECTED = "pii_detected"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    SECURITY_THREAT = "security_threat"

@dataclass
class GuardrailViolation:
    type: GuardrailViolationType
    severity: str  # "low", "medium", "high", "critical", "competitor"
    message: str
    matched_text: str
    confidence: float
    action: str  # "block", "sanitize", "flag"

class RAGGuardrails:
    def __init__(self):
        # Load configuration from environment
        self.langfuse = Langfuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://langfuse-web:3000"),
        )
        
        # Sensitive patterns
        self.sensitive_patterns = {
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b",
            "api_key": r"\b[A-Za-z0-9]{32,}\b",
            "password": r"(?i)password[:\s]*[A-Za-z0-9!@#$%^&*]{6,}",
            "token": r"(?i)(token|jwt)[:\s]*[A-Za-z0-9._-]{20,}",
            "secret": r"(?i)(secret|key)[:\s]*[A-Za-z0-9!@#$%^&*]{8,}",
            "internal_ip": r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\b172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}\b|\b192\.168\.\d{1,3}\.\d{1,3}\b",
        }
        
        # Competitor companies (customize for your industry)
        self.competitors = [
            "Emerson", "Johnson Controls", "Honeywell", "Siemens",
            # Add your specific competitors
        ]
        
        # Sensitive keywords that should be filtered
        self.sensitive_keywords = [
            "confidential", "proprietary", "internal", "classified",
            "trade secret", "patent pending", "ndaa", "restricted",
            "salary", "compensation", "budget", "financial", "revenue",
            "acquisition", "merger", "layoffs", "restructuring",
            "vulnerability", "exploit", "backdoor", "security flaw", "kill", "exploit", "attack vector", "penetration test", "phishing", "malware", "ransomware",
            "ddos", "denial of service", "sql injection", "xss",
            "buffer overflow", "cross site scripting", "malicious code", "cyber attack", "data breach", "hacking", "penetration testing",
            "social engineering", "insider threat", "zero day exploit", "advanced persistent threat"

        ]
        
        # Security threat patterns
        self.security_patterns = [
            r"(?i)(sql\s+injection|xss|cross.?site|buffer\s+overflow)",
            r"(?i)(malware|virus|trojan|ransomware)",
            r"(?i)(hack|exploit|penetration\s+test)",
            r"(?i)(ddos|denial\s+of\s+service)",
        ]
    
    def scan_query(self, query: str, user_id: str = None) -> Tuple[bool, List[GuardrailViolation]]:
        """Scan user query for violations"""
        violations = []
        
        # Check for sensitive data patterns
        violations.extend(self._check_sensitive_patterns(query))
        
        # Check for competitor mentions
        violations.extend(self._check_competitors(query))
        
        # Check for sensitive keywords
        violations.extend(self._check_sensitive_keywords(query))
        
        # Check for security threats
        violations.extend(self._check_security_threats(query))
        
        # Log violations to Langfuse
        if violations:
            self._log_violations(query, violations, user_id, "query")
        
        # Determine if query should be blocked
        should_block = any(v.action == "block" for v in violations)
        
        return should_block, violations
    
    def scan_response(self, response: str, sources: List[str] = None, user_id: str = None) -> Tuple[str, List[GuardrailViolation]]:
        """Scan and sanitize response"""
        violations = []
        sanitized_response = response
        
        # Check response for violations
        violations.extend(self._check_sensitive_patterns(response))
        violations.extend(self._check_competitors(response))
        violations.extend(self._check_sensitive_keywords(response))
        
        # Sanitize response
        for violation in violations:
            if violation.action in ["sanitize", "block"]:
                sanitized_response = self._sanitize_text(sanitized_response, violation)
        
        # Check sources for violations
        if sources:
            for source in sources:
                source_violations = self._check_competitors(source, context="source")
                violations.extend(source_violations)
        
        # Log violations
        if violations:
            self._log_violations(response, violations, user_id, "response")
        
        return sanitized_response, violations
    
    def _check_sensitive_patterns(self, text: str) -> List[GuardrailViolation]:
        """Check for sensitive data patterns"""
        violations = []
        
        for pattern_name, pattern in self.sensitive_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(GuardrailViolation(
                    type=GuardrailViolationType.SENSITIVE_DATA,
                    severity="high" if pattern_name in ["ssn", "credit_card", "api_key"] else "medium",
                    message=f"Detected {pattern_name.replace('_', ' ')}",
                    matched_text=match.group(),
                    confidence=0.9,
                    action="sanitize" if pattern_name in ["email", "phone"] else "block"
                ))
        
        return violations
    
    def _check_competitors(self, text: str, context: str = "content") -> List[GuardrailViolation]:
        """Check for competitor mentions"""
        violations = []
        
        for competitor in self.competitors:
            pattern = rf"\b{re.escape(competitor)}\b"
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(GuardrailViolation(
                    type=GuardrailViolationType.COMPETITOR_MENTION,
                    severity="competitor",
                    message=f"Competitor mention: {competitor}",
                    matched_text=match.group(),
                    confidence=0.8,
                    action="block"
                ))
        
        return violations
    
    def _check_sensitive_keywords(self, text: str) -> List[GuardrailViolation]:
        """Check for sensitive business keywords"""
        violations = []
        
        for keyword in self.sensitive_keywords:
            pattern = rf"\b{re.escape(keyword)}\b"
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                severity = "high" if keyword in ["confidential", "proprietary", "trade secret"] else "medium"
                action = "block" if severity == "high" else "flag"
                
                violations.append(GuardrailViolation(
                    type=GuardrailViolationType.SENSITIVE_DATA,
                    severity=severity,
                    message=f"Sensitive keyword: {keyword}",
                    matched_text=match.group(),
                    confidence=0.7,
                    action=action
                ))
        
        return violations
    
    def _check_security_threats(self, text: str) -> List[GuardrailViolation]:
        """Check for security threats"""
        violations = []
        
        for pattern in self.security_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                violations.append(GuardrailViolation(
                    type=GuardrailViolationType.SECURITY_THREAT,
                    severity="critical",
                    message="Security threat detected",
                    matched_text=match.group(),
                    confidence=0.85,
                    action="block"
                ))
        
        return violations
    
    def _sanitize_text(self, text: str, violation: GuardrailViolation) -> str:
        """Sanitize text by removing or replacing violations"""
        if violation.type == GuardrailViolationType.SENSITIVE_DATA:
            # Replace with redacted placeholder
            if "email" in violation.message.lower():
                return text.replace(violation.matched_text, "[EMAIL_REDACTED]")
            elif "phone" in violation.message.lower():
                return text.replace(violation.matched_text, "[PHONE_REDACTED]")
            elif "ssn" in violation.message.lower():
                return text.replace(violation.matched_text, "[SSN_REDACTED]")
            else:
                return text.replace(violation.matched_text, "[REDACTED]")
        
        elif violation.type == GuardrailViolationType.COMPETITOR_MENTION:
            pattern = re.escape(violation.matched_text)
            return re.sub(pattern, "We sell DwyerOmega products. We do not have much information about the company you mentioned.", text, flags=re.IGNORECASE)
            # Replace competitor names with generic terms
            # replacements = {
            #     "emerson": "a competitor",
            #     "johnson controls": "a competitor",
            #     "honeywell": "a competitor",
            #     "siemens": "a competitor",
            # }
            # competitor_name = violation.matched_text.lower()
            # replacement = replacements.get(competitor_name, "a competitor")
            # return text.replace(violation.matched_text, replacement)
        
        return text
    
    def _log_violations(self, content: str, violations: List[GuardrailViolation], user_id: str, content_type: str):
        """Log violations to Langfuse for monitoring"""
        try:
            self.langfuse.trace(
                name="guardrail_violation",
                input={
                    "content_type": content_type,
                    "content_hash": hashlib.md5(content.encode()).hexdigest()[:16],
                    "violation_count": len(violations)
                },
                output={
                    "violations": [
                        {
                            "type": v.type.value,
                            "severity": v.severity,
                            "message": v.message,
                            "confidence": v.confidence,
                            "action": v.action
                        } for v in violations
                    ]
                },
                user_id=user_id,
                metadata={
                    "guardrail_version": "1.0",
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Failed to log violation: {e}")
    
    def get_safe_error_message(self, violations: List[GuardrailViolation]) -> str:
        """Generate user-friendly error message"""
        if not violations:
            return "Request processed successfully."
        
        severity_counts = {}
        for violation in violations:
            severity_counts[violation.severity] = severity_counts.get(violation.severity, 0) + 1
        
        if "critical" in severity_counts:
            return "I cannot process this request as it contains potentially harmful content."
        elif "competitor" in severity_counts:
            return "I’m sorry, I cannot provide information about other company. Please ask about DwyerOmega products."
        elif "high" in severity_counts:
            return "I cannot provide this information as it contains sensitive data."
        elif "medium" in severity_counts:
            return "I've filtered some content from my response for privacy and security reasons."
        else:
            return "Your request has been processed with some content filtered."

# Global guardrails instance
guardrails = RAGGuardrails()