# Training Outputs

Screenshots and terminal logs from each training phase.

## Structure

```
training_outputs/
├── phase1_fpgrowth/        FP-Growth trainer output
│   └── (terminal screenshot showing itemsets mined, top tokens, artifact path)
│
├── phase2_distilbert/      DistilBERT fine-tuning
│   └── (per-epoch val-F1/AUC, test set results, confusion matrix)
│
├── phase3_url_whois/       URL+WHOIS intelligence module
│   └── (sample URL scoring output, WHOIS latency stats)
│
└── phase6_vector_store/    FAISS vector index build
    └── (index size, embedding time, sample nearest-neighbour results)
```

## What to screenshot for each phase

| Phase | What to capture |
|---|---|
| Phase 1 — FP-Growth | Full terminal output: dataset sizes, vocabulary pruning, itemset counts, top-10 tokens, artifact path |
| Phase 2 — DistilBERT | Per-epoch table (train_loss / val_F1 / val_AUC) + final TEST SET RESULTS block + confusion matrix |
| Phase 3 — URL+WHOIS | Sample API response showing `url_whois_score` and per-URL feature breakdown |
| Phase 6 — Vector store | Index build log: n_embeddings, index size, sample `similar_examples` from a query |
