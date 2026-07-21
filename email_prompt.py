EMAIL_PROMPT = """
Draft a professional email to a vendor about invoice discrepancies, following 
these instructions:
{instructions}

Depending on the reason behind the discrepancies, your email might be directed to different people:
- If the internal reference is the one to be corrected, address the email to "GoWestTours Hotel Operations".
- If the invoice is the one to be corrected, address the email to the supplier.

Discrepancies found:
{explanations}

Email Examples:
1 - Email for internal reference correction:
Hello Ate Tricia,

Could you update the rate for this group? It seems like the base used in Access does not match with the one in contract.

Here is the contract.

Thank you!

Best regards,
Leigh

2 - Email for internal reference correction:
Hello At Tricia,

I hope all is well.

Could you confirm if a smoke fee is okay with this group?

Suppliers	Date	Group Name
La Quinta Inn & Suites Scottsdale	Fri, 7/17/26	IREO-SFSF12N


Thank you!

Best regards,
Leigh

3 - Email for the supplier:
Hello,
I hope this message finds you well.
This is to confirm that we have received your invoice. However upon checking the contract, it seems that we are not liable for any incidentals including smoking fees. You may see a snippet fro our contract:
snip of contract
 
Could you also have it reviewed and let us know?
Thank you for your cooperation, and I wish you a pleasant day ahead.
Best regards,
Leigh

4 - Email for the supplier:
Hello,
 
I hope you’re doing well.
 
This is to confirm that we have received your invoice. However upon checking, it appears that you billed us with a wrong rate of $169.00 per room, but this is the contracted rate we have with you:

[user will insert screenshot of contract here]

Could you recheck this and send us the revised invoice once confirmed?
 
Thank you, and I wish you a pleasant day ahead.
 
Best regards,
Leigh

Important:
- If writting to the supplier you should always politely ask the supplier to review the 
  invoice with an open question, like the examples above ("Could you review ...?") 
- Emails to suppliers should start with: 
  "Hello,
  
  I hope you are doing well."
- All emails should end with:
  "Best regards, 
  Leigh"  

Return only the email body, no subject line, no commentary.
"""