# Dataset & Test Sample Guidelines

## Data Directories
- `data/samples/`: Clean standard sample identity documents for baseline verification.
- `data/synthetic/`: Consented synthetic test identity cards and passports.
- `data/test_cases/`: Edge cases (e.g. blurred images, mismatched DOBs, expired passports, manipulated photos).
- `data/uploads/`: Ingested input files (runtime).
- `data/outputs/`: Generated heatmaps, masks, cropped portraits (runtime).

## Privacy & Security Rules
- **No Sensitive PII:** Do not upload real non-consented citizen identity records to public version control.
- All testing for the hackathon prototype utilizes open synthetic benchmarks (MIDV-500, MIDV-2020, SIDTD).
