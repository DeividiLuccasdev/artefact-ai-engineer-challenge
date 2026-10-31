# Recorded evaluation

## Environment and evidence

Local Qwen3 1.7B Q4_K_M via llama.cpp, supplied CSV snapshot f0fa33f3c17aa0c4,
and store manual v2.1. Four English conversations are recorded in examples/.
These are actual application outputs. Where templates are used, the record is an
execution of the hybrid agent, not a claim that the LLM independently wrote the text.

## Issues observed and addressed

- Generic acoustic search terms narrowed a category query incorrectly. Category
  adjectives are normalized for Violões; an exact model name takes precedence over
  an inconsistent category supplied by the model.
- An initial model answer gave the wrong return-shipping payer without consulting
  the manual. Local provider requests now require tools for recognized store-fact
  queries. Query aliases and relative relevance filtering improve policy retrieval.
- Even after retrieval, the model invented a 24-hour return window. A narrow return
  template is now used only when the retrieved passage contains the seven-day and
  store-paid return-shipping rules. Other policy answers still require broader evals.
- The model invented prices or explained PIX stacking incorrectly. Product answers
  now render values directly from the most recent product tool result. Empty results
  cannot produce a price through that template.

## Final recorded scenarios

1. Catalog: three available Violões under BRL 1,000; all quoted amounts and stock
   quantities match the product tool result.
2. Online return: page 4 retrieved; seven calendar days after actual receipt and
   store-paid return freight are explained without approving a refund.
3. Promotion: Ohana CK-20, original BRL 549.00, 20% promotion, final BRL 439.20.
   No extra PIX discount is added.
4. Privacy/scope: claimed chat identity cannot authorize order 1; tracking is not
   disclosed. A subsequent cake-recipe request is redirected to store support.

## Limits

The four scenarios are not a comprehensive model benchmark. Mixed product/policy
questions may need follow-up because the product template takes precedence. Tool
selection and unconstrained policy prose remain model-dependent. Keyword-based tool
requirements do not cover every paraphrase or language. Error messages default to
Portuguese. Demo identity selection in the CLI is not authentication. The visual
demo deliberately denies all order queries. No real inventory writes are performed.

27 automated tests passed after the grounding changes. Public repository upload
is pending write access. The submission PDF is marked as a review copy until that
upload is complete; no form submission or recruiter email has been sent.
