# Launch Checklist

Complete this checklist before launching OpenFix v0.1.0.

---

## ✅ Pre-Release Verification

### Code Quality
- [ ] All unit tests passing (16/16)
- [ ] No `print()` statements in production code
- [ ] Code formatted with `black`
- [ ] No hardcoded secrets or API keys
- [ ] Type hints added to public APIs

### Documentation
- [ ] README.md reviewed for accuracy
- [ ] All example commands tested
- [ ] CONTRIBUTING.md includes setup instructions
- [ ] LICENSE file present (MIT)
- [ ] RELEASE_NOTES.md complete

### Functionality
- [ ] Issue discovery works
- [ ] Patch generation functional
- [ ] Validation harness runs
- [ ] PR creation tested (sandbox)
- [ ] CLI commands functional

---

## 🏗️ GitHub Repository Setup

### 1. Create Repository

```bash
# From openfix directory
gh repo create openfix --public --source=. --remote=origin

# Or manually:
# 1. Go to https://github.com/new
# 2. Name: openfix
# 3. Description: AI-powered GitHub issue solver
# 4. Public repository
# 5. Don't initialize with README (we have one)
```

### 2. Configure Repository Settings

**Topics to add:**
- `ai`
- `github-actions`
- `automation`
- `code-generation`
- `python`
- `gemini`

**Repository features:**
- ✅ Issues enabled
- ✅ Pull requests enabled
- ✅ Discussions enabled
- ✅ Wiki disabled

### 3. Add Secrets (for testing GitHub Action)

Go to Settings → Secrets and variables → Actions:

Required secrets:
- `GEMINI_API_KEY` - Your Gemini API key
- `GITHUB_TOKEN` - Automatically provided by GitHub

---

## 🔑 Required Environment Variables

For local development and testing:

```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc)
export GEMINI_API_KEY="your-gemini-api-key-here"
export GITHUB_TOKEN="your-github-token-here"

# Or create .env file in project root
echo "GEMINI_API_KEY=your-key" >> .env
echo "GITHUB_TOKEN=your-token" >> .env
```

**Get API Keys:**
- Gemini API: https://ai.google.dev/
- GitHub Token: https://github.com/settings/tokens (needs `repo` scope)

---

## 🧪 Testing Commands

### Discover Issues
```bash
python scripts/cli.py discover https://github.com/monkeytypegame/monkeytype-bot --limit 5
```

**Expected output:**
- Finds open issues
- Triages with AI
- Saves to `artifacts/issues.json`
- Shows priority scores

### Solve Issue
```bash
python scripts/cli.py solve https://github.com/monkeytypegame/monkeytype-bot --issue 81
```

**Expected output:**
- Generates patch
- Shows confidence score
- Displays diff preview
- Asks for approval

### Full Automation
```bash
python scripts/automate_full_pipeline.py \
  --repo-url https://github.com/monkeytypegame/monkeytype-bot
```

**Expected output:**
- Runs discovery
- Generates patch for top issue
- Validates patch
- Creates report

---

## 🎪 Sandbox Testing

### Create Test Repository

```bash
python scripts/setup_sandbox.py --path openfix-sandbox
cd openfix-sandbox

# Follow printed instructions to:
# 1. Create GitHub repo
# 2. Push code
# 3. Create test issue
# 4. Run OpenFix on it
```

### Validate End-to-End

```bash
python scripts/cli.py solve https://github.com/YOUR_USERNAME/openfix-sandbox --issue 1
```

**Should produce:**
- Patch fixing division by zero
- Confidence score > 60
- Draft PR (if --create-pr used)

---

## 🚀 Release Creation

### 1. Tag and Push

```bash
# Ensure all changes committed
git add .
git commit -m "feat: initial release v0.1.0"

# Create tag
git tag -a v0.1.0 -m "OpenFix v0.1.0 - AI-powered issue solver"

# Push to origin
git push origin main
git push origin v0.1.0
```

### 2. Create GitHub Release

**Via CLI:**
```bash
gh release create v0.1.0 \
  --title "OpenFix v0.1.0 - Initial Release" \
  --notes-file RELEASE_NOTES.md \
  --latest
```

**Or manually:**
1. Go to https://github.com/CodeRustyPro/openfix/releases/new
2. Tag: `v0.1.0`
3. Title: `OpenFix v0.1.0 - Initial Release`
4. Description: Copy from `RELEASE_NOTES.md`
5. Check "Set as latest release"
6. Click "Publish release"

---

## 📣 Launch Preparation

### Before Going Public

- [ ] Run full test suite
- [ ] Test on 2-3 real repositories
- [ ] Verify GitHub Action works
- [ ] Check README renders correctly on GitHub
- [ ] Review all public documentation
- [ ] Prepare demo video (optional)
- [ ] Draft HN post (see HN_POST.md)

### Social Media Assets

**Screenshots to capture:**
1. CLI patch preview with confidence score
2. Draft PR with AI disclosure
3. GitHub Action workflow running
4. Sandbox test repository

**Demo repositories:**
- OpenFix sandbox
- Real fix on popular repo (with permission)

---

## 📊 Post-Launch Monitoring

### First 24 Hours

- [ ] Monitor GitHub stars/forks
- [ ] Respond to issues within 2 hours
- [ ] Track HN discussion
- [ ] Fix any critical bugs immediately

### First Week

- [ ] Gather user feedback
- [ ] Create FAQ from common questions
- [ ] Plan v0.1.1 bug fixes
- [ ] Start v0.2.0 roadmap

---

## ✨ Launch Platforms

1. **Hacker News** - Use HN_POST.md
2. **Reddit** - r/programming, r/Python, r/MachineLearning
3. **Twitter/X** - Thread with screenshots
4. **Dev.to** - Full blog post
5. **Product Hunt** - Launch listing

---

**Ready to launch!** 🚀
