# Europe DevOps Job Automation — Visa Sponsorship MVP

This project helps a DevOps / Cloud Engineer automatically discover Europe-based openings that mention visa sponsorship or relocation support, score them against the candidate profile, generate a tailored cover letter, and prepare an application queue for review.

> Important: this system is intentionally **human-in-the-loop**. It does not blindly submit applications to LinkedIn, Workday, Greenhouse, Lever, or company career sites. Many job sites prohibit automated submissions, and forms often contain legal consent questions. The safe design is: automate discovery, scoring, CV/cover-letter creation, and reminders; approve each application before final submission.

## Candidate profile used

The default config is tuned for Rahul Prajapati, a DevOps / Cloud Engineer with strong experience in GCP, AWS, Azure, Terraform, Kubernetes, Helm, ArgoCD, GitLab CI/CD, Cloud Run, Anthos/Istio, observability, and internal DevOps automation.

Target roles:

- DevOps Engineer
- Cloud Engineer
- Platform Engineer
- Site Reliability Engineer
- Infrastructure Engineer
- Kubernetes Engineer

Target countries:

- Germany
- Netherlands
- Ireland
- United Kingdom
- Sweden
- Spain
- Portugal
- Denmark
- Finland

## What it automates

```mermaid
flowchart LR
    A[Scheduled Job<br/>GitLab CI / GitHub Actions / Cloud Scheduler] --> B[Job Sources]
    B --> B1[Arbeitnow API<br/>visa_sponsorship=true]
    B --> B2[Greenhouse public job boards]
    B --> B3[Lever public job boards]
    B --> C[Normalizer + Deduper]
    C --> D[Visa & relocation filter]
    D --> E[Skill matching + scoring]
    E --> F[(SQLite job database)]
    F --> G[Generate cover letter<br/>per job]
    G --> H[Application queue CSV]
    H --> I[Human approval]
    I --> J[Manual submit / Gmail draft / ATS API only if allowed]
```

## Recommended architecture on GCP

```mermaid
flowchart TD
    CS[Cloud Scheduler<br/>Daily 8 AM IST] --> CRJ[Cloud Run Job<br/>jobbot discover]
    CRJ --> SM[Secret Manager<br/>API keys / Slack webhook]
    CRJ --> SQL[(Cloud SQL / SQLite on GCS for MVP)]
    CRJ --> GCS[Cloud Storage<br/>CV + generated cover letters]
    CRJ --> SLACK[Slack notification<br/>top matched roles]
    USER[You] --> APPROVAL[Approval queue CSV / simple UI]
    APPROVAL --> APPLY[Apply manually or create Gmail drafts]
```

For the first version, run it from GitLab CI schedule or GitHub Actions. Move to Cloud Run Job when it is stable.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

Put your CV PDF at:

```bash
data/Rahul_Prajapati.pdf
```

Then run:

```bash
python -m jobbot discover --config config/config.yaml
python -m jobbot package --config config/config.yaml --min-score 70
```

Outputs:

```text
data/jobs.sqlite
out/application_queue.csv
out/applications/<company>-<role>/cover_letter.md
out/applications/<company>-<role>/metadata.json
```

## How scoring works

A role gets a score out of 100:

- +25 for role/title match: DevOps, Cloud, Platform, SRE, Infrastructure, Kubernetes
- +30 for skill match: GCP, Kubernetes, Terraform, Helm, ArgoCD, GitLab CI, Cloud Run, Istio, observability, Prometheus, Grafana, Signoz, Teleport, Python, Go
- +25 for visa/relocation signal: visa sponsorship, relocation assistance, Blue Card, work permit sponsorship
- +10 for Europe target location match
- +10 for seniority fit
- hard reject if text says: no visa sponsorship, must already have work authorization, EU citizenship required, sponsorship unavailable

## Automation modes

### 1. Safe default: `draft_only`

Creates cover letters and an application queue. You review and submit manually.

### 2. Gmail draft mode: `gmail_draft`

Creates Gmail drafts only for companies where a hiring/recruiting email is explicitly present in the job post. It does not send automatically.

### 3. ATS API mode: `ats_api_approved`

Only use this when:

- the ATS officially supports application submission via API,
- you have valid credentials/API keys,
- the target company/job permits API submission,
- the job is marked approved in `application_queue.csv`.

## GitLab scheduled pipeline

Create a GitLab CI/CD schedule for daily discovery:

```yaml
stages:
  - discover

job_search:
  image: python:3.12-slim
  stage: discover
  before_script:
    - pip install -r requirements.txt
  script:
    - python -m jobbot discover --config config/config.yaml
    - python -m jobbot package --config config/config.yaml --min-score 70
  artifacts:
    when: always
    paths:
      - out/
      - data/jobs.sqlite
```

## Google Sheets application queue

The GitHub Actions workflow can push `out/application_queue.csv` into a Google
Sheet after every run. This gives you an Excel-like tracking sheet without
running a web app or database. Existing rows are kept by `apply_url`, and any
manual `status` changes in Google Sheets are preserved on the next sync.

### One-time GCP setup

1. Create or select a GCP project.
2. Enable the **Google Sheets API**, **IAM Service Account Credentials API**,
   and **Security Token Service API**.
3. Create a service account, for example `jobbot-sheets-writer`.
4. Configure Workload Identity Federation for the GitHub repo.
5. Create a Google Sheet named something like `Europe DevOps Application Queue`.
6. Share the Google Sheet with the service account email as **Editor**. The
   service account does not need broad project-level Editor access.
7. Copy the spreadsheet ID from the Sheet URL:

```text
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
```

Example GCP setup commands:

```bash
export PROJECT_ID="your-gcp-project-id"
export REPO="Rahulkprajapati/eu-jobs"
export SERVICE_ACCOUNT="jobbot-sheets-writer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud services enable \
  sheets.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="${PROJECT_ID}"

gcloud iam service-accounts create "jobbot-sheets-writer" \
  --project="${PROJECT_ID}" \
  --display-name="Jobbot Sheets Writer"

gcloud iam workload-identity-pools create "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc "eu-jobs" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github" \
  --display-name="eu-jobs GitHub Actions" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository == '${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

export WORKLOAD_IDENTITY_POOL_ID="$(gcloud iam workload-identity-pools describe "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format="value(name)")"

gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${REPO}"

gcloud iam workload-identity-pools providers describe "eu-jobs" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github" \
  --format="value(name)"
```

The final command prints the provider resource name used for the
`GCP_WORKLOAD_IDENTITY_PROVIDER` secret.

### GitHub secrets

Add these under **GitHub repo -> Settings -> Secrets and variables -> Actions**:

```text
GCP_WORKLOAD_IDENTITY_PROVIDER = projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/eu-jobs
GCP_SERVICE_ACCOUNT = jobbot-sheets-writer@PROJECT_ID.iam.gserviceaccount.com
GOOGLE_SHEET_ID = the spreadsheet ID from the Google Sheet URL
```

Do not create or store a service account JSON key for GitHub Actions. If the old
`GCP_SERVICE_ACCOUNT_JSON` secret exists, remove it after confirming Workload
Identity works.

The existing `.github/workflows/daily-job-search.yml` will then:

1. Discover jobs.
2. Generate `out/application_queue.csv`.
3. Sync the queue into the `Application Queue` tab in Google Sheets.
4. Still upload the CSV and generated cover letters as a GitHub artifact.

For local testing, authenticate with Application Default Credentials and run:

```bash
export JOBBOT_GOOGLE_SHEETS_ENABLED=true
export GOOGLE_SHEET_ID="your-spreadsheet-id"
gcloud auth application-default login
python -m jobbot sync-sheets --config config/config.yaml
```

## Best daily workflow

1. Run the scheduled discovery every morning.
2. Review the `Application Queue` Google Sheet or `out/application_queue.csv`.
3. For every good role, open the apply URL.
4. Use the generated cover letter.
5. Track status in Google Sheets: `new`, `approved`, `applied`, `rejected`, `interview`, `offer`.

## Notes for Europe visa sponsorship

For Germany, keep salary thresholds in mind because EU Blue Card eligibility depends on job offer, contract duration, matching qualification, and salary threshold. For the Netherlands, the employer is the sponsor and IT professionals may use education or qualifying experience routes depending on the permit.
