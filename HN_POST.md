# Hacker News Launch Post

## Title Candidates

**Option 1 (Technical):**
"OpenFix – AI-powered GitHub issue solver with automated PR creation"

**Option 2 (Benefit-focused):**
"OpenFix – Turn GitHub issues into pull requests automatically with AI"

**Option 3 (Provocative):**
"OpenFix – An AI that actually fixes bugs (not just finds them)"

**Recommended:** Option 2 (clear value proposition)

---

## One-Sentence Pitch

**Primary:**
"OpenFix uses Gemini AI to automatically discover GitHub issues, generate patches, validate them, and create draft PRs with confidence scoring."

**Alternative:**
"An open-source AI agent that scans your GitHub repo, picks fixable bugs, writes patches, validates them, and opens draft PRs for review."

---

## Post Body

### Paragraph 1: The Hook
I built OpenFix to solve a problem I kept seeing: GitHub repos filled with fixable bugs that maintainers don't have time to address. What if an AI could automatically scan issues, generate patches, validate them, and create draft PRs for review? That's OpenFix – an end-to-end pipeline from issue discovery to pull request.

### Paragraph 2: How It Works
OpenFix uses Gemini 2.0 to analyze your repository and open issues. It triages issues by suitability for automated fixing, selects relevant code chunks using semantic search (FAISS), generates patches, runs validation tests, and if validation fails, iteratively repairs the patch using feedback loops. Each patch gets a confidence score (0-100) based on triage priority, complexity, validation results, and repair iterations. High-confidence patches can trigger automatic draft PR creation.

### Paragraph 3: Key Features
The system includes an interactive CLI with beautiful Rich UI for patch preview and approval, GitHub Actions integration for full automation (just label an issue with "openfix"), and comprehensive safety features: all PRs are drafts with AI disclosure, risk labels, and human review checklists. I've also built a sandbox generator that creates test repos with intentional bugs, perfect for trying it out safely. The entire pipeline is logged, tested (16 unit tests), and production-ready.

### Paragraph 4: Why I Made This & What's Next
I wanted to explore what's actually possible with AI code generation today – not just autocomplete, but autonomous bug fixing with validation and iteration. The results are promising: it successfully generates patches for medium-complexity Python bugs. Current limitations include Python-only support and dependency on runnable test suites. The roadmap includes multi-language support (JS, Go, Rust), enhanced validation with static analysis, learning from past fixes, and a web dashboard. It's MIT licensed and ready for contributors. Try it on your own repos and let me know what works (and what breaks).

---

## Screenshots to Capture

### 1. CLI Patch Preview
- Terminal showing confidence score (51.4/100)
- Risk rating (High/Medium/Low)
- Syntax-highlighted diff preview
- Approval prompt

### 2. GitHub PR
- Draft PR with AI disclosure banner
- Confidence assessment section
- Review checklist
- Link to artifacts

### 3. GitHub Action
- Workflow running on labeled issue
- Successful patch generation
- PR creation confirmation

### 4. Architecture Diagram
- Visual pipeline flow
- Discovery → Triage → Generate → Validate → Repair → Score → PR

---

## Call to Action

**Primary CTA:**
"Try it out: `git clone https://github.com/CodeRustyPro/openfix.git` and run the sandbox generator to test safely."

**Secondary CTA:**
"I'd love feedback on what types of issues it handles well (and poorly). Contributions welcome!"

**Link:**
https://github.com/CodeRustyPro/openfix

---

## Pre-Post Checklist

Before submitting to HN:

- [ ] All 4 screenshots captured and polished
- [ ] Demo video recorded (optional but recommended)
- [ ] GitHub repo README renders perfectly
- [ ] Test sandbox works flawlessly
- [ ] At least one real-world example PR ready to show
- [ ] Prepared to respond to comments quickly (first 2 hours critical)

---

## Expected Questions & Responses

**Q: Does it really work?**
A: Yes, with caveats. Works well on medium-complexity Python bugs with runnable tests. Struggles with complex multi-file changes or issues requiring deep domain knowledge.

**Q: What about hallucinations?**
A: That's why we have validation loops and confidence scoring. Low-confidence patches require manual review. All PRs are drafts.

**Q: Token costs?**
A: Variable. Small repos: ~$0.10-0.50 per issue. Large repos: $1-5. Using Gemini Flash to keep costs down.

**Q: Why not Claude/GPT-4?**
A: Gemini 2.0 Flash offers excellent quality at lower cost. System is model-agnostic – could swap easily.

**Q: Production ready?**
A: For supervised use, yes. Don't auto-merge without review. Think of it as a very capable intern.

---

## Timing Strategy

**Best times to post:**
- Tuesday-Thursday
- 9-11 AM ET
- Avoid Friday evenings, weekends

**Engagement plan:**
- Respond to all comments within 1 hour (first 2 hours)
- Be humble about limitations
- Share technical details when asked
- Follow up with blog post after 24h

---

**Good luck with the launch!** 🚀
