# Question Bank Streamlit

Private Streamlit assessment app for ML/infrastructure engineering interviews.

## Local development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
APP_ENV=development python -m src.seed
APP_ENV=development streamlit run app/Home.py
```

Development auth is available only when `APP_ENV=development`. Production uses Streamlit OIDC (`st.login`, `st.user`) and then checks the local allowlist in `users`.

Do not run `python -m src.seed` against production data; it creates local demo users only.

Deployment notes live in [DEPLOYMENT.md](DEPLOYMENT.md).

Seed users:

- `interviewer@example.com`
- `candidate1@example.com`
- `candidate2@example.com`

## Configuration

- `APP_ENV`: `development` enables the local auth selector. Anything else fails closed behind OIDC.
- `DB_PATH`: sqlite database path. Defaults to `data/app.sqlite3`.
- `STORAGE_BACKEND`: `local` or `s3`.
- `STORAGE_DIR`: local object store directory.
- `S3_BUCKET`, `S3_ENDPOINT_URL`: S3-compatible object storage settings.
- `MAX_UPLOAD_MB`: final ZIP size limit.

## Workflow

Candidates see instructions before the challenge is revealed. Starting the assessment records server-side timestamps and refreshes do not reset the timer. After expiry, responses and uploads become read-only. The app uses one global 90-minute assessment timer and records soft section time estimates for interviewer review.

Submissions are stored as immutable ZIP artifacts. The app records SHA-256, size, filename, timestamp, and revision history.

Interviewers can view assignment state, written answers, revision history, and download the latest or any earlier submitted ZIP. Private local contract tests live under `challenges/segmentation_v1/hidden/tests` and are excluded from Git. After downloading and extracting a submission, run them from your local checkout with `CANDIDATE_ROOT=/path/to/extracted/segmentation_v1 python -m pytest challenges/segmentation_v1/hidden/tests`. The app does not execute submissions automatically.

## Runner boundary

The Streamlit app never executes candidate code. Its queue action only records a request; no worker is configured. Run downloaded submissions in an isolated environment.

## Tests

```bash
python -m unittest
```
