# Adapter Contract

The harness does not require a specific vector DB or orchestration framework. An adapter executes each gold query against the target RAG and writes one canonical JSONL record per case matching `schemas/run_case.schema.json`.

Required minimum output:

```json
{"id":"Q001","retrieved":["DOC1#C3","DOC2#C8"],"abstained":false}
```

Document/chunk identifiers MUST be stable enough to match gold relevance labels. Adapters SHOULD also emit retrieval scores, final answer, citations, latency, cost, errors, and stack/model/index metadata.

Possible adapters include Qdrant, Pinecone, pgvector/PostgreSQL, Elasticsearch/OpenSearch, GraphRAG/knowledge-graph systems, local FAISS, hosted RAG APIs, and custom pipelines. Stack-specific behavior belongs here, not in the scoring engine.
