# TCS NQT AIML Interview — Domain Notes

## Candidate Profile (Rekapalli Vasudeva)
- BTech ECE 2026, Mohan Babu University, CGPA 8.59
- Skills: Python, OOPs, DSA, ML, DL, MySQL, PyTorch, sklearn, matplotlib, seaborn, Docker (basics), FastAPI (basics)
- Projects: AI Text Summarizer (T5-small + SAMSum + FastAPI + Render), GI Adenocarcinoma CNN
- Certs: Apna College AIML, Oracle OCI AI Foundations
- GitHub: RekapalliVasudeva-MBU | HuggingFace: ValtareVasu/text_summarizer
- This is his first interview — TCS NQT AIML shortlisted May 2026

## Key Technical Topics to Cover

### ML Fundamentals
- Bagging vs Boosting (Random Forest vs XGBoost)
- Overfitting prevention (regularization, dropout, early stopping, cross-validation)
- Bias-variance tradeoff
- Precision, Recall, F1-score, ROC-AUC
- Cross-validation techniques

### Deep Learning
- CNN architecture (convolution, pooling, fully connected)
- RNN/LSTM/GRU — vanishing gradient problem
- Attention mechanism and Transformers (Q, K, V)
- Transfer learning (ResNet, VGG fine-tuning)
- Data augmentation techniques

### NLP
- Tokenization, stemming, lemmatization
- Word embeddings (Word2Vec, GloVe)
- Transformer architecture (encoder-decoder)
- T5 vs BART vs GPT-2 for summarization
- ROUGE metrics (ROUGE-1, ROUGE-2, ROUGE-L)

### Python/OOPs
- List vs tuple (mutability)
- Decorators (@syntax)
- *args and **kwargs
- Class vs static method
- Inheritance and polymorphism

## Project Talking Points

### Text Summarizer
- Fine-tuned T5-small on SAMSum (4000 dialogues, 6 epochs)
- T5 chosen for text-to-text framework, lightweight (60M params)
- Deployed via FastAPI on Render using HuggingFace Inference API
- ROUGE scores for evaluation
- Why not BART/GPT-2: BART heavier, GPT-2 not encoder-decoder

### GI Adenocarcinoma CNN
- Binary/multi-class classification of histopathology images
- Data augmentation + transfer learning
- [User should fill in accuracy metrics]

## Industry Awareness Talking Points
- Indian ecommerce: Flipkart vs Amazon vs Tata Cliq
- Tata Cliq pivot: 42% sales drop FY24, exited electronics, now fashion/beauty (Tata Cliq Palette)
- ML challenge in category pivots: cold start, different user behavior patterns, return rates
- Omnichannel retail as differentiator

## HR Answers (Memorized)
- Relocation: Fully flexible
- 5-year plan: Senior AI/ML engineer leading projects
- Why TCS: Opportunity to work on production AI systems at scale
- Questions to ask: Team's current projects, tech stack, NLP/CV opportunities

## Pro Tips for This Candidate
1. Mention GitHub and HuggingFace links — shows seriousness
2. Be honest about basics (Docker, FastAPI) — say "I know the fundamentals and can build on them"
3. If stuck on a question: "I'm not sure about that specifically, but here's what I know about [related topic]..."
4. Keep answers 1-2 minutes max
5. This is his first interview — confidence matters more than perfection
