# OpenFix 🤖

> AI-powered GitHub issue solver that automatically discovers bugs, generates patches, and creates pull requests.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## ✨ Features

- 🔍 **Automatic Issue Discovery** - Scans repositories and triages issues by likelihood of automated fix
- 🛠️ **AI Patch Generation** - Uses Gemini AI to generate code patches with validation
- 🔄 **Iterative Repair** - Self-improving patches through validation feedback loops
- 📊 **Confidence Scoring** - Risk assessment (0-100) for each generated patch
- 🎯 **Draft PR Creation** - Automatically creates PRs with AI disclosure and review checklist
- ⚡ **GitHub Actions** - Full CI/CD integration for automated workflows
- 🖥️ **Interactive CLI** - Beautiful terminal UI for patch review and approval

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/CodeRustyPro/openfix.git
cd openfix

# Install dependencies
pip install -r requirements.txt

# Configure API keys
export GEMINI_API_KEY="your-gemini-api-key"
export GITHUB_TOKEN="your-github-token"
```

### Basic Usage

```bash
# 1. Discover issues in a repository
python agents/discovery/discover_issues.py https://github.com/owner/repo

# 2. Generate a patch for a specific issue (interactive)
python scripts/cli.py solve https://github.com/owner/repo --issue 123

# 3. Full automation (discover + patch + PR)
python scripts/automate_full_pipeline.py \\
  --repo-url https://github.com/owner/repo \\
  --create-pr
```

---

## 📖 Usage Guide

### CLI Commands

**Discover Issues:**
```bash
python scripts/cli.py discover https://github.com/owner/repo --limit 10
```

**Solve with Approval:**
```bash
python scripts/cli.py solve https://github.com/owner/repo --issue 42
# Shows confidence score, diff preview, asks for approval
```

**Auto-Approve (CI mode):**
```bash
python scripts/cli.py solve https://github.com/owner/repo --issue 42 --no-confirm
```

**Check Status:**
```bash
python scripts/cli.py status
```

### GitHub Action

Add `.github/workflows/openfix.yml`:

```yaml
name: OpenFix
on:
  issues:
    types: [labeled]

jobs:
  fix:
    if: contains(github.event.issue.labels.*.name, 'openfix')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: CodeRustyPro/openfix-action@v1
        with:
          gemini-api-key: \${{ secrets.GEMINI_API_KEY }}
          github-token: \${{ secrets.GITHUB_TOKEN }}
```

Label any issue with `openfix` and the bot automatically generates a fix!

---

## 🔧 Configuration

### Environment Variables

- `GEMINI_API_KEY` - **Required** for AI patch generation
- `GITHUB_TOKEN` - **Required** for PR creation, optional for read-only operations

### Config File

Edit `config/config.yml`:

```yaml
llm:
  model: "gemini-2.0-flash-exp"
  temperature: 0.3
  max_retries: 2

validation:
  enabled: true
  timeout: 300

patch:
  max_files: 5
  confidence_threshold: 60
```

---

## 📊 Confidence Scoring

OpenFix calculates a 0-100 confidence score for each patch:

| Score | Risk | Recommendation |
|-------|------|----------------|
| 75-100 | Low | High confidence - Consider auto-merge |
| 50-74 | Medium | Review recommended |
| 0-49 | High | Manual review required |

**Scoring Factors:**
- Triage Priority (25%)
- Issue Complexity (20%)
- Validation Results (35%) 
- Repair Iterations (20%)

---

## 🧪 Testing

### Sandbox Testing

```bash
# Create test repository
python scripts/setup_sandbox.py

# Follow instructions to create GitHub repo
# Then test OpenFix on it
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/

# Full test suite
pytest tests/ -v --cov=.
```

---

## 🛡️ Safety Features

- ✅ **Draft PRs Only** - Never auto-merges
- ✅ **AI Disclosure** - Clear attribution in every PR
- ✅ **Review Checklist** - Ensures human oversight
- ✅ **Risk Labeling** - High-risk patches clearly marked
- ✅ **Validation** - Automated testing before PR creation

---

## 🏗️ Architecture

```
OpenFix Pipeline:
┌─────────────┐
│   Discover  │ → Scan repo for issues
└──────┬──────┘
       │
┌──────▼──────┐
│   Triage    │ → Filter & rank by suitability
└──────┬──────┘
       │
┌──────▼──────┐
│  Generate   │ → AI creates patch
└──────┬──────┘
       │
┌──────▼──────┐
│  Validate   │ → Run tests & checks
└──────┬──────┘
       │
┌──────▼──────┐
│   Repair    │ → Refine based on feedback
└──────┬──────┘
       │
┌──────▼──────┐
│ Create PR   │ → Draft PR with disclosure
└─────────────┘
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Powered by [Google Gemini AI](https://ai.google.dev/)
- Built with [PyGithub](https://github.com/PyGithub/PyGithub)
- UI by [Rich](https://github.com/Textualize/rich)

---

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/CodeRustyPro/openfix/issues)
- **Discussions**: [GitHub Discussions](https://github.com/CodeRustyPro/openfix/discussions)
- **Email**: devshah3@illinois.edu

---

**Made with ❤️ by the OpenFix Team**
