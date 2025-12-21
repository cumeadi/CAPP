"""
Prompt Templates for Compliance Agent
"""

COMPLIANCE_ANALYSIS_SYSTEM_PROMPT = """
You are an expert Regulatory Compliance Officer for a cross-border payment system in Africa.
Your job is to analyze transaction details, screen against sanctions lists (provided in context), and evaluate money laundering risks.

You must output your decision in strict JSON format.
"""

TRANSACTION_SCREENING_PROMPT = """
Analyze the following transaction for compliance risks.

Transaction Details:
- Sender: {sender_name} ({sender_country})
- Recipient: {recipient_name} ({recipient_country})
- Amount: {amount} {currency}
- Payment Method: {payment_method}
- Description: {description}

Context / Sanctions Hits:
The following potential matches were found in the database (fuzzy match):
{sanctions_matches}

Regulatory Rules:
- {sender_country} Limit: {sender_limit}
- {recipient_country} Limit: {recipient_limit}

Task:
1. Determine if this transaction violates any sanctions or AML rules.
2. Assign a risk score (0.0 - 1.0).
3. Provide a clear reasoning for your decision.

Output JSON Format:
{{
    "is_compliant": boolean,
    "risk_score": float,
    "reasoning": "string",
    "violations": ["string", ...],
    "required_actions": ["string", ...]
}}
"""
