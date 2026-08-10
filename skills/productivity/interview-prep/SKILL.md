---
name: interview-prep
description: Prepare for job interviews — frame questions, craft answers, and build prep plans tailored to the user's resume, target role, and company. Use when user asks for interview questions, mock interview prep, "why should we hire you", "tell me about yourself", or any interview coaching request.
---

# Interview Prep

## Trigger

User asks for interview preparation, mock questions, answer framing, or company/role-specific prep.

## Workflow

1. **Gather context** — Get the user's resume (PDF or text), target role, target company, and interview type (technical, HR, behavioral). If resume is a PDF, note that direct extraction may fail; rely on user-provided details or memory.

2. **Structure the output** — Always cover these sections:
   - **Tell Me About Yourself** — 30-45 second pitch
   - **Why Should We Hire You** — Value proposition
   - **Project Deep-Dives** — 2-3 questions per project with STAR-format answers
   - **Technical Questions** — Role-specific (ML/DL/NLP for AIML roles)
   - **HR/Behavioral Questions** — Relocation, salary, 5-year plan
   - **Questions to Ask the Interviewer** — 2-3 smart questions

3. **Keep answers concise** — User prefers practical, direct answers. No long paragraphs. Each answer should be 2-4 sentences max in the prep doc (user will expand verbally).

4. **Include pro tips** — Add 2-3 tactical tips at the end (e.g., "mention GitHub/HuggingFace links", "if you don't know, say what you DO know").

## Pitfalls

- **Don't fabricate metrics** — If the user hasn't provided specific numbers (accuracy, ROUGE scores, etc.), use placeholders like `[mention your accuracy]%` and tell them to fill it in.
- **Don't cite unverified claims** — If the user references a news article or market fact they can't source, advise them to either verify it or reframe as a general technical discussion. Better to say "From an ML perspective, category pivots are hard because..." than to cite a specific percentage without a source.
- **PDF resumes may not be readable** — Binary PDFs can't be read directly. Use `memory` to recall known user profile details, or ask the user to paste key sections.
- **Adapt to the role** — AIML interviews need ML/DL/NLP questions. Full-stack interviews need system design. Always match technical questions to the job description.

## Output Format

Use this template:

```
# [Company] [Role] — Interview Q&A Prep

## 1. Tell Me About Yourself
[Concise pitch with name, education, key skills, top project, career goal]

## 2. Why Should We Hire You
[Value proposition — what you bring, not what you want]

## 3. Project-Based Questions
### Q: [Question]
**A:** [2-4 sentence answer with specific technical detail]

## 4. Technical Questions
[Role-specific questions and answers]

## 5. HR Questions
[Relocation, salary, 5-year plan, etc.]

## 6. Questions to Ask the Interviewer
[2-3 questions that show genuine interest]

## Pro Tips
[Tactical advice specific to this interview]
```

## Reference Files

- `references/tcs-nqt-aiml.md` — Candidate profile, domain notes, and talking points for TCS NQT AIML interview (Rekapalli Vasudeva, May 2026). Load when preparing for this specific interview.

## Verification

- All project answers reference real projects from the user's resume
- Technical questions match the target role's domain
- No fabricated metrics without placeholders
- Pro tips are actionable, not generic
