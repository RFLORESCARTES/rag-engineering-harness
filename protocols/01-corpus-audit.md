# Corpus audit protocol

Inventory sources, file types, versions, ownership, parsing status, chunk counts,
duplicate families, access restrictions, and stable document identifiers. Sample
parsed text against source content. Stop as `BLOCKED` when provenance is missing,
restricted data are exposed, or extraction cannot be verified. Do not tune
retrieval until ingestion defects are separated from retrieval defects.
For R1-R3, reject every document lacking either a non-empty `tenant_id` or an
explicit shared scope and non-empty `allowed_tenants`. Legacy or unclassified
documents are blockers, never implicitly public.
