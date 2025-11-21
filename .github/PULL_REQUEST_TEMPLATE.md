## 📋 Description

<!-- Provide a brief description of your changes -->

## 🔗 Related Issue

<!-- Link to the issue this PR addresses -->
Closes #

## 🎯 Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test coverage improvement
- [ ] 🏗️ Infrastructure/DevOps changes

## 🧪 Testing

<!-- Describe the tests you ran and how to reproduce them -->

- [ ] Unit tests pass locally
- [ ] Integration tests pass
- [ ] Manual testing performed
- [ ] Added new tests for new features

### Test Instructions

```bash
# Commands to test your changes
pytest tests/
```

## 📸 Screenshots

<!-- If applicable, add screenshots or GIFs demonstrating the changes -->

## ✅ Checklist

<!-- Mark completed items with an 'x' -->

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

### For Database Changes

- [ ] Database migrations are idempotent (use IF NOT EXISTS)
- [ ] Migration rollback tested
- [ ] Migration tested on clean database
- [ ] Data integrity validation added

### For Infrastructure Changes

- [ ] `terraform validate` passes
- [ ] `terraform fmt` applied
- [ ] No hardcoded secrets or credentials
- [ ] TFSec scan passed
- [ ] Documentation updated

### For Security-Sensitive Changes

- [ ] Security implications reviewed
- [ ] No secrets committed
- [ ] Gitleaks scan passed
- [ ] Input validation implemented
- [ ] Authentication/authorization checked

## 📝 Additional Notes

<!-- Any additional information that reviewers should know -->

## 🔍 Reviewer Guidance

<!-- Help reviewers focus on specific areas -->

**Focus areas for review:**
- 
- 

**Questions for reviewers:**
- 
- 

---

**By submitting this PR, I confirm:**
- [ ] I have read the [CONTRIBUTING](../CONTRIBUTING.md) guidelines
- [ ] I have read the [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md)
- [ ] I understand this project follows the [MIT License](../LICENSE)
