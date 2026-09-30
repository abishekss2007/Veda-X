## Summary
<!-- Brief description of the changes proposed in this PR -->

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Security / Compliance enhancement
- [ ] Documentation update
- [ ] Refactor / CI/CD pipeline

## Security & Compliance Checklist
- [ ] No secrets, keys, or passwords committed (`.env` remains untracked)
- [ ] Role-Based Access Control (RBAC) enforced on backend (JWT validation)
- [ ] Tamper-proof audit logging included for sensitive operations
- [ ] Input validation and SQL injection prevention verified

## Testing
- [ ] Local tests pass: `python -m pytest backend/tests -v -o pythonpath=backend`
- [ ] Frontend JavaScript syntax verified: `node --check`
