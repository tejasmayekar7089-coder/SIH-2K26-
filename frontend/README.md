# SIH26188 — Officer Dashboard UI (Frontend)

The Officer Dashboard is the primary visual decision-support interface for border and identity verification officers.

## Key Principles
1. **AI Assists • Officer Decides:** The UI presents clear evidence, heatmaps, and reason codes, but never makes automated rejections.
2. **Multi-Column Visual Evidence:**
   - Column 1: Document OCR fields & MRZ check digits.
   - Column 2: Tampering AI heatmaps & 1:1 facial biometric matching.
   - Column 3: Composite risk score & officer action buttons (`[ACCEPT / CLEAR]`, `[SECONDARY REVIEW]`, `[REJECT / FRAUD]`).

## Development
```bash
# Install dependencies
npm install

# Start local development server
npm run dev
```
