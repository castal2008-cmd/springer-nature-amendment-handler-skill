# Springer Nature Amendment Handler

An AI-powered automation skill for handling **Springer Nature manuscript amendments, revisions, and transfer submissions**. Built from experience processing 38+ submissions across 6 batches, this skill automates the entire workflow from dashboard scanning to final submission.

## Overview

This skill automates the tedious process of handling Springer Nature manuscript amendments by:
- Scanning the SNAPP dashboard for pending items
- Retrieving amendment requirements from Gmail
- Downloading and analyzing manuscripts for common issues
- Automatically fixing problems (uncited figures/references, missing declarations, etc.)
- Re-uploading corrected files and submitting via browser automation
- Generating comprehensive processing reports

## Key Features

- **Dashboard Scanning** — Automated extraction of all actionable submissions (amendments, revisions, transfers)
- **Dual Platform Support** — Works with both SNAPP (modern) and MTS (legacy) submission systems
- **Manuscript Analysis** — Detects uncited figures, uncited references, missing declarations, word count issues
- **Automated Fixes** — Programmatic correction of common technical check failures
- **Gmail Integration** — Retrieves amendment requirements via MCP tools
- **Point-by-Point Response** — Structured revision response document generation
- **Browser Automation** — File upload, form filling, and submission via browser tools
- **Batch Processing** — Processes all pending items in a single session until dashboard is cleared

## Supported Workflows

| Flow | Trigger | Description |
|------|---------|-------------|
| **Amendment** | "Amendment required" on dashboard | Fix and resubmit manuscripts that failed technical checks |
| **Revision** | "Submit revision" on dashboard | Revise with point-by-point response to reviewer comments |
| **Transfer** | "Incomplete submission" on dashboard | Complete journal transfer submissions |

## Common Issues Detected & Fixed

| Issue | Automated Fix |
|-------|--------------|
| Uncited figures | Add figure citations at contextually relevant paragraphs |
| Uncited references | Add reference citations matching paragraph topics |
| Missing figure files | Generate placeholder figures |
| Word count too low | Flag for manual expansion |
| Missing Data Availability | Add standard statement |
| Missing Ethics/Consent | Add declaration sections |
| Cover letter format (.txt) | Convert to .docx or .pdf |
| Title mismatch | Update via Quill editor |
| Missing declarations | Add standard statements |

## Included Files

\`\`\`
springer-nature-amendment-handler/
├── SKILL.md                          # Complete workflow instructions
├── scripts/
│   ├── fix_manuscript.py             # Manuscript analyzer and fixer
│   ├── generate_figures.py           # Placeholder figure generator
│   ├── verify_citations.py           # Citation verification (PubMed, CrossRef)
│   └── snapp_cdp_upload.py           # CDP upload utility (deprecated)
└── references/
    └── snapp-troubleshooting.md      # Platform-specific workarounds
\`\`\`

## Key Lessons (from 38+ submissions)

1. **All amendments must be fully processed** — never skip analysis
2. **Dashboard is the source of truth** — Gmail is supplementary
3. **XHR download is the most reliable** for SNAPP manuscripts
4. **Cover letters must be .pdf or .docx** — .txt files are rejected
5. **MTS requires explicit PDF validation** before submission
6. **Process until dashboard is cleared** — don't stop after partial completion

## Support This Project

If you find this skill useful, please consider supporting its development:

- [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/castal2008)
- [![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/castal2008-cmd)

### Bank Transfer (Taiwan)

| Field | Details |
|-------|---------|
| **Bank** | Yuanta Bank (元大銀行) |
| **Bank Code** | 806 |
| **Account Number** | 00211020001960​29 |
| **Account Holder** | Shenghan Chen (陳聖翰) |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
