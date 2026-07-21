EMAIL_PROMPT = """
Draft a professional email to a vendor about invoice discrepancies, following 
these instructions:
{instructions}

Depending on the reason behind the discrepancies, your email might be directed to different people:
- If the internal reference is the one to be corrected, address the email to "GoWestTours Hotel Operations".
- If the invoice is the one to be corrected, address the email to the supplier.

Discrepancies found:
{explanations}

Return only the email body, no subject line, no commentary.
"""