# Promotion and PIX - acceptance scenario

Status: authored scenario; live transcript pending.

Customer: Show an available instrument with an active promotion.

Expected behavior: search the catalog, verify promotion_active in returned results.
If the first results have no promotion, refine the search rather than invent one.
Present original price, discount percentage and final promotional price.

Customer: Can I add the five percent PIX discount?

Expected behavior: search policy rules and refresh the quote with payment="pix".
Explain that the manual does not allow PIX stacking on a promotional price.
The final amount must equal the code-calculated promotional price.
