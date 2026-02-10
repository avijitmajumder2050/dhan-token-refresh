# Trading Data Automation Workflow

## Overview

This repository contains an automated system to retrieve stock OHLC data and refresh access tokens using the DHAN API. The workflow leverages **AWS EventBridge, Lambda, EC2, Docker, and Python DHAN SDK**, ensuring automated data processing every trading day.

---

## Sequence Flow

### 1. Scheduled Trigger

- **AWS EventBridge Scheduler** triggers **AWS Lambda** every **trading day at 8:00 AM IST**.
- Lambda orchestrates EC2 instance launch for the automated job.

### 2. EC2 Instance Launch

- Lambda retrieves **EC2 Launch Template ID** from **AWS Parameter Store**.
- Lambda launches an EC2 instance using the template.
- The EC2 instance runs a **bootstrap shell script** (`user-data`) that:
  1. Pulls **GitHub repository** URL from Parameter Store.
  2. Pulls required **Docker images** from **AWS ECR**.
  3. Executes the first Docker container for **token refresh**.

### 3. Docker Container 1: Token Refresh

- Retrieves **client ID and client secret** from **Parameter Store**.
- Uses **Python DHAN SDK** to renew the **access token**.
- **Retry logic:** If token refresh fails, retries every 2 minutes until successful.
- Once the token is retrieved:
  - Writes the **access token** to Parameter Store.
  - Exits the container after 1 minute.

### 4. Docker Container 2: OHLC Data Retrieval

- Pulls **second Docker image**.
- Retrieves **access token** from Parameter Store.
- Reads the list of stocks from **S3 CSV file**.
- Uses **DHAN SDK** to fetch **200-day historical OHLC data** for each stock.
- Saves the retrieved CSV files back to **S3**.

### 5. Post-Processing and Cleanup

- Sends a **Telegram notification** indicating job completion.
- EC2 instance is **automatically terminated** using **AWS SDK** to save costs.

---

## Technologies Used

- **AWS Services:** Lambda, EC2, EventBridge, S3, Parameter Store, ECR
- **Docker:** Containerized tasks for token refresh and OHLC data retrieval
- **Python:** DHAN SDK, Pandas
- **CI/CD:** GitHub repository for code versioning
- **Monitoring & Notifications:** Telegram API for job status

---

## Workflow Diagram (Sequence)

```text
AWS EventBridge (8:00 AM IST)
        |
        v
AWS Lambda
        |
        v
Retrieve EC2 Launch Template from Parameter Store
        |
        v
Launch EC2 Instance with Bootstrap Script
        |
        +---------------------------+
        |                           |
        v                           v
Docker Container 1            Docker Container 2
(Token Refresh)               (OHLC Data)
  - Fetch client ID             - Get access token
  - Renew token                 - Read stock CSV from S3
  - Retry every 2 min            - Pull 200-day OHLC via DHAN SDK
  - Write token to Parameter     - Save CSV to S3
    Store                        - Exit
  - Exit container
        |
        v
Notify via Telegram
        |
        v
Terminate EC2 instance
## Deployment Steps

1. **EventBridge Scheduler**
   - Configure **AWS EventBridge** rule to trigger every **trading day at 8:00 AM IST**.

2. **Lambda Function**
   - Create **AWS Lambda** to launch an EC2 instance using a **Launch Template**.
   - Lambda reads **Launch Template ID** from **AWS Parameter Store**.

3. **Parameter Store Setup**
   - Store secrets and configuration:
     - GitHub repository URL
     - DHAN client ID / client secret
     - EC2 Launch Template ID
     - Access token (written by first container)

4. **EC2 Launch Template**
   - Configure **user-data bootstrap script** to:
     - Pull code from GitHub
     - Pull Docker images from **AWS ECR**
     - Run Docker containers sequentially:
       1. Token refresh container
       2. OHLC data fetch container

5. **Docker Containers**
   - **Container 1: Token Refresh**
     - Retrieve client ID/secret from Parameter Store
     - Renew access token using **DHAN Python SDK**
     - Retry every 2 minutes until successful
     - Save access token to Parameter Store
     - Exit after 1 minute
   - **Container 2: OHLC Data Fetch**
     - Pull access token from Parameter Store
     - Read stock list from **S3 CSV**
     - Retrieve 200-day OHLC historical data using DHAN SDK
     - Save CSVs back to S3

6. **Post-Processing**
   - Notify completion via **Telegram**
   - Auto-terminate EC2 using **AWS SDK** to save costs

---

## Visual Sequence Flow Chart

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant Lambda as AWS Lambda
    participant PS as Parameter Store
    participant EC2 as EC2 Instance
    participant Docker1 as Docker Container 1 (Token Refresh)
    participant Docker2 as Docker Container 2 (OHLC Fetch)
    participant S3 as S3 Bucket
    participant Telegram as Telegram

    EB->>Lambda: Trigger at 8:00 AM IST
    Lambda->>PS: Get EC2 Launch Template ID
    Lambda->>EC2: Launch instance with bootstrap script
    EC2->>PS: Get GitHub repo URL
    EC2->>EC2: Pull GitHub code
    EC2->>Docker1: Start container (Token Refresh)
    Docker1->>PS: Get client ID / secret
    Docker1->>DHAN: Refresh access token
    Docker1->>PS: Write access token
    Docker1-->>EC2: Exit container
    EC2->>Docker2: Start container (OHLC Fetch)
    Docker2->>PS: Read access token
    Docker2->>S3: Read stock list CSV
    Docker2->>DHAN: Fetch 200-day OHLC data
    Docker2->>S3: Save stock CSVs
    Docker2-->>EC2: Exit container
    EC2->>Telegram: Notify job completion
    EC2->>EC2: Auto-terminate


## AWS BSS Automation Architecture

```mermaid
flowchart TD
    %% EventBridge triggers Lambda
    EB(EventBridge Scheduler)
    Lambda(AWS Lambda)
    PS[Parameter Store]
    EC2(EC2 Instance)
    Docker1[Docker Container 1<br>(Token Refresh)]
    Docker2[Docker Container 2<br>(OHLC Fetch)]
    GitHub[GitHub Repository]
    ECR[AWS ECR Docker Images]
    S3[S3 Bucket for Stock CSVs]
    DHAN[DHAN API]
    Telegram[Telegram Notification]

    %% EventBridge triggers Lambda
    EB -->|Trigger every trading day 8:00 AM IST| Lambda
    Lambda -->|Read Launch Template ID| PS
    Lambda -->|Launch EC2 instance with bootstrap script| EC2

    %% EC2 bootstrap actions
    EC2 -->|Pull GitHub code| GitHub
    EC2 -->|Pull Docker images| ECR
    EC2 -->|Start Docker 1| Docker1

    %% Docker 1 actions: Token Refresh
    Docker1 -->|Read clientID/secret| PS
    Docker1 -->|Call DHAN API to refresh token| DHAN
    Docker1 -->|Write access token| PS
    Docker1 -->|Exit container| EC2

    %% Docker 2 actions: OHLC fetch
    EC2 -->|Start Docker 2| Docker2
    Docker2 -->|Read access token| PS
    Docker2 -->|Read stock list CSV| S3
    Docker2 -->|Call DHAN API to fetch 200-day OHLC data| DHAN
    Docker2 -->|Write stock CSVs| S3
    Docker2 -->|Exit container| EC2

    %% Post-processing
    EC2 -->|Send job completion message| Telegram
    EC2 -->|Auto-terminate| EC2

    style EB fill:#f9f,stroke:#333,stroke-width:2px
    style Lambda fill:#bbf,stroke:#333,stroke-width:2px
    style PS fill:#ff9,stroke:#333,stroke-width:2px
    style EC2 fill:#bfb,stroke:#333,stroke-width:2px
    style Docker1 fill:#fc9,stroke:#333,stroke-width:2px
    style Docker2 fill:#fc9,stroke:#333,stroke-width:2px
    style GitHub fill:#ccf,stroke:#333,stroke-width:2px
    style ECR fill:#ccf,stroke:#333,stroke-width:2px
    style S3 fill:#ffc,stroke:#333,stroke-width:2px
    style DHAN fill:#fdd,stroke:#333,stroke-width:2px
    style Telegram fill:#9ff,stroke:#333,stroke-width:2px

