# Diagnosis and controlled-improvement loop

Repeat only within the registered budget and stop conditions:

1. identify the first failing mandatory dimension;
2. select the smallest causal layer capable of producing it;
3. state one falsifiable hypothesis;
4. register one primary variable and predicted movement;
5. run baseline and candidate on identical frozen inputs;
6. compare per-query changes and every mandatory gate;
7. accept only without regression or new blocker;
8. convert the corrected failure into a regression test;
9. stop on budget exhaustion, repeated neutral results, mutation, or a critical event.

Do not loop by rewriting prompts blindly. Retrieval, metadata, authorization,
reranking, context assembly, generation, and output filtering are distinct layers.
