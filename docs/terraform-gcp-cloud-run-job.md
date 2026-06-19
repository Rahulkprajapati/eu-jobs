# Optional GCP deployment design

Use this after the MVP is stable locally or in GitLab CI.

## Components

- Cloud Scheduler: triggers daily job search.
- Cloud Run Job: runs `python -m jobbot discover` and `python -m jobbot package`.
- Secret Manager: stores Slack webhook, optional Gmail credentials, and ATS keys.
- Cloud Storage: stores generated cover letters and CV packages.
- Cloud SQL or Firestore: stores job records and application status.

## Flow

```mermaid
sequenceDiagram
    participant Scheduler as Cloud Scheduler
    participant RunJob as Cloud Run Job
    participant Sources as Job Sources
    participant DB as Cloud SQL / Firestore
    participant Storage as Cloud Storage
    participant Slack as Slack
    participant User as Rahul

    Scheduler->>RunJob: Trigger daily discovery
    RunJob->>Sources: Fetch visa-sponsored DevOps jobs
    Sources-->>RunJob: Job JSON
    RunJob->>DB: Upsert scored jobs
    RunJob->>Storage: Save cover letters + metadata
    RunJob->>Slack: Send top matches
    User->>DB: Mark approved/applied
```
