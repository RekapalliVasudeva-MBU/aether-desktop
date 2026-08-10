# TCS AIML Interview — Resume & Project Tips

## Resume Red Flags for ML/AI Roles

- **"Runs locally only"** — This signals no deployment experience. For any paid AI role (6-7 LPA+), deploy your project publicly. HuggingFace Spaces is free and takes 10 minutes.
- **No metrics on projects** — "Built a summarizer" is weak. "Fine-tuned T5-small on 4000 dialogues, achieved X ROUGE score, deployed at URL" is strong.
- **Vague profile summary** — "have experience using local ai ecosystem using Hermes AI Agent" means nothing to recruiters. Replace with concrete skills.

## Keywords TCS AIML Looks For

- Python, PyTorch, Transformers, FastAPI/REST API
- Model fine-tuning, evaluation metrics (accuracy, ROUGE, F1)
- Docker (basics), Git, SQL
- RAG, LLM Agents, LangChain (bonus, not required for entry-level)
- Computer Vision (CNN, classification)

## Project Bullet Format

Use this pattern:
```
• [Action] [what] on [dataset/tech] ([scale]) → [measurable result]
```

Examples:
- Fine-tuned T5-small on SAMSum dataset (4000 dialogues, 6 epochs) for abstractive summarization
- Developed REST API using FastAPI with HTML/CSS/JS frontend; deployed at [public URL]
- Built end-to-end CNN pipeline for EUS image classification; applied model optimization to reduce size by X%

## TCS NQT AIML Interview Topics

1. **Python coding** — DSA, OOPs basics
2. **ML concepts** — bias-variance, overfitting, regularization, cross-validation
3. **DL basics** — CNN architecture, RNN vs Transformer, attention mechanism
4. **Project deep-dive** — Expect detailed questions on every project listed
5. **SQL** — JOINs, GROUP BY, subqueries
6. **Aptitude/Reasoning** — From the NQT test itself

## Deployment = Resume Multiplier

A live demo URL on a resume is worth more than 3 extra bullet points. For TCS and similar companies:
- **HuggingFace Spaces** (free, 16GB RAM) — Best for ML demos
- **Render** (free tier 512MB) — Only for lightweight apps, NOT PyTorch models
- **Railway** ($5 credit) — Good middle ground
