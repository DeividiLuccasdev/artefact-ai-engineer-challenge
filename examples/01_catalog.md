# Catalog and context - acceptance scenario

Status: authored scenario; live transcript pending.

Customer: Which acoustic guitars are available for up to BRL 1,000?

Expected behavior: call search_products with category="Violões", max_price_brl="1000",
available_only=true. Show only matching active products and tool-derived prices.
Explain snapshot availability does not reserve stock.

Customer: And if I pay with PIX?

Expected behavior: preserve the category and budget from this session; query again
with payment="pix". Do not reuse a stale quote. Show the actual returned final price.
