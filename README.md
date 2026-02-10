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

## Full Trading Data Automation Flow

```mermaid
flowchart TD
    %% Participants / Nodes
    EB["1. EventBridge Scheduler"]
    Lambda["2. AWS Lambda"]
    PS["3. Parameter Store"]
    EC2["4. EC2 Instance"]
    Docker1["5. Docker Container 1 - Token Refresh"]
    Docker2["6. Docker Container 2 - OHLC Fetch"]
    GitHub["7. GitHub Repository"]
    ECR["8. AWS ECR Docker Images"]
    S3["9. S3 Bucket for Stock CSVs"]
    DHAN["10. DHAN API"]
    Telegram["11. Telegram Notification"]

    %% Sequence / Flow
    EB -->|Trigger daily 8:00 AM IST| Lambda
    Lambda -->|Read Launch Template ID| PS
    Lambda -->|Launch EC2 instance| EC2

    EC2 -->|Pull GitHub code| GitHub
    EC2 -->|Pull Docker images| ECR
    EC2 -->|Start Docker 1 (Token Refresh)| Docker1

    Docker1 -->|Read client ID/secret| PS
    Docker1 -->|Call DHAN API to refresh token| DHAN
    Docker1 -->|Write access token| PS
    Docker1 -->|Exit container| EC2

    EC2 -->|Start Docker 2 (OHLC Fetch)| Docker2
    Docker2 -->|Read access token| PS
    Docker2 -->|Read stock list CSV| S3
    Docker2 -->|Call DHAN API to fetch 200-day OHLC data| DHAN
    Docker2 -->|Save CSVs| S3
    Docker2 -->|Exit container| EC2

    EC2 -->|Send job completion notification| Telegram
    EC2 -->|Auto-terminate| EC2

    %% Styling
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

