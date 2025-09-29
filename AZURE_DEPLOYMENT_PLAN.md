# Azure Deployment Plan - Sports Betting Analytics Platform

## 🏗️ Infrastructure Overview

### Core Services
- **Azure App Service** - Streamlit web application hosting
- **Azure Database for PostgreSQL** - Primary database for betting analytics
- **Azure Container Instances** - Scheduled data collection scripts
- **Azure Functions** - Lightweight triggers and utilities
- **Azure Key Vault** - Secure secrets management
- **Azure Container Registry** - Docker image storage
- **Azure Monitor/Application Insights** - Logging and monitoring

## 📊 Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Azure App     │    │  Azure Database  │    │  Azure Container│
│    Service      │◄──►│  for PostgreSQL  │◄──►│   Instances     │
│  (Streamlit)    │    │                  │    │ (Data Scripts)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Azure Key      │    │  Azure Monitor   │    │ The Odds API    │
│     Vault       │    │   + Insights     │    │  (External)     │
│   (Secrets)     │    │  (Monitoring)    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Deployment Components

### 1. Azure App Service (Streamlit Application)

#### Configuration
- **Runtime:** Python 3.11
- **Pricing Tier:** B2 Basic (2 cores, 3.5GB RAM) - scalable to P1V3 for production
- **Operating System:** Linux
- **Deployment:** Docker container or Git deployment

#### Environment Variables
```bash
# Database Configuration
DB_HOST=your-postgres-server.postgres.database.azure.com
DB_PORT=5432
DB_NAME=betting_analytics
DB_USER=postgres_admin
DB_PASSWORD=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/db-password/)

# API Keys
CLAUDE_API_KEY=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/claude-api-key/)
ODDS_API_KEY=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/odds-api-key/)

# Application Settings
PYTHONPATH=/home/site/wwwroot
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "dynamic_nfl_reports.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 2. Azure Database for PostgreSQL

#### Configuration
- **Service Tier:** General Purpose
- **Compute Size:** 2 vCores, 8GB RAM (B2s for dev, GP_Gen5_2 for production)
- **Storage:** 100GB SSD with auto-growth enabled
- **Backup:** 7-day retention, geo-redundant
- **SSL:** Enabled (required)

#### Security
- **Firewall Rules:** 
  - Allow Azure services
  - Allow App Service subnet
  - Allow Container Instances subnet
- **Connection Security:** SSL enforced
- **Authentication:** Azure AD integration + SQL authentication

#### Initial Database Setup
```sql
-- Create database
CREATE DATABASE betting_analytics;

-- Create application user
CREATE USER app_user WITH ENCRYPTED PASSWORD 'secure_password_from_keyvault';
GRANT CONNECT ON DATABASE betting_analytics TO app_user;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
```

### 3. Azure Container Instances (Data Collection)

#### Container Groups
1. **Initial Data Setup Container** (One-time)
2. **Scheduled Data Collection Container** (Recurring)

#### Container Registry Setup
```bash
# Create container registry
az acr create --resource-group sports-betting-rg --name sportsbettingcr --sku Basic

# Build and push images
az acr build --registry sportsbettingcr --image data-setup:latest ./scripts/setup/
az acr build --registry sportsbettingcr --image data-collector:latest ./scripts/scheduled/
```

## 📋 Data Population Strategy

### One-Time Setup Scripts

#### 1. Database Schema Initialization
**Script:** `scripts/setup/init_database.py`
```python
# Initialize database schema
# Create tables: games, teams, sports, bookmakers, spreads, moneylines, totals
# Create views: spread_movements, game_results, moneyline_movements
# Create indexes for performance
```

#### 2. Teams and Sports Population
**Script:** `scripts/setup/populate_reference_data.py`
```python
# Populate sports table (NFL, NBA, NCAAF, NCAAB)
# Populate teams for each sport
# Populate bookmakers (DraftKings, FanDuel, BetMGM, etc.)
```

#### 3. Historical Data Backfill
**Script:** `scripts/setup/backfill_historical_data.py`
```python
# Backfill 2023-2024 seasons for all sports
# Use The Odds API with rate limiting
# Process in chunks to avoid API limits
# Estimated runtime: 4-6 hours
```

#### Container Configuration (One-time)
```yaml
apiVersion: 2019-12-01
location: eastus
name: betting-setup
properties:
  containers:
  - name: database-setup
    properties:
      image: sportsbettingcr.azurecr.io/data-setup:latest
      resources:
        requests:
          cpu: 1
          memoryInGb: 2
      environmentVariables:
      - name: DB_HOST
        secureValue: your-postgres-server.postgres.database.azure.com
      - name: ODDS_API_KEY
        secureValue: your-odds-api-key
  restartPolicy: Never
  osType: Linux
```

### Scheduled Data Collection Scripts

#### 1. Current Odds Collection
**Script:** `scripts/scheduled/collect_current_odds.py`
**Schedule:** Every 15 minutes during active seasons
**Purpose:** Collect live spreads, moneylines, totals for upcoming games

#### 2. Game Results Collection
**Script:** `scripts/scheduled/collect_game_results.py`
**Schedule:** Every hour
**Purpose:** Update completed games with final scores

#### 3. Historical Snapshots
**Script:** `scripts/scheduled/collect_historical_snapshots.py`
**Schedule:** Every 6 hours
**Purpose:** Collect point-in-time odds for line movement analysis

#### Azure Container Instances (Scheduled)
```yaml
apiVersion: 2019-12-01
location: eastus
name: betting-data-collector
properties:
  containers:
  - name: odds-collector
    properties:
      image: sportsbettingcr.azurecr.io/data-collector:latest
      resources:
        requests:
          cpu: 0.5
          memoryInGb: 1
      environmentVariables:
      - name: COLLECTION_TYPE
        value: "current_odds"
      - name: DB_HOST
        secureValue: your-postgres-server.postgres.database.azure.com
  restartPolicy: Always
  osType: Linux
```

## ⏰ Scheduling Strategy

### Azure Logic Apps (Recommended)
```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "triggers": {
      "Recurrence": {
        "recurrence": {
          "frequency": "Minute",
          "interval": 15
        }
      }
    },
    "actions": {
      "Create_Container_Instance": {
        "type": "Http",
        "inputs": {
          "method": "PUT",
          "uri": "https://management.azure.com/subscriptions/{subscription}/resourceGroups/{rg}/providers/Microsoft.ContainerInstance/containerGroups/odds-collector-{timestamp}",
          "headers": {
            "Authorization": "Bearer {access_token}"
          },
          "body": {
            "location": "eastus",
            "properties": {
              "containers": [...]
            }
          }
        }
      }
    }
  }
}
```

### Alternative: Azure Functions + Timer Triggers
```python
import azure.functions as func
import subprocess

def main(mytimer: func.TimerRequest) -> None:
    # Trigger container instance creation
    # Monitor execution
    # Handle failures and retries
    pass
```

## 🔐 Security & Configuration

### Azure Key Vault Secrets
```bash
# Create Key Vault
az keyvault create --name sports-betting-vault --resource-group sports-betting-rg

# Add secrets
az keyvault secret set --vault-name sports-betting-vault --name "db-password" --value "your-secure-db-password"
az keyvault secret set --vault-name sports-betting-vault --name "claude-api-key" --value "your-claude-api-key"
az keyvault secret set --vault-name sports-betting-vault --name "odds-api-key" --value "your-odds-api-key"
```

### Managed Identity Setup
```bash
# Create user-assigned managed identity
az identity create --name sports-betting-identity --resource-group sports-betting-rg

# Assign Key Vault access
az keyvault set-policy --name sports-betting-vault --object-id {identity-principal-id} --secret-permissions get list
```

## 📊 Monitoring & Logging

### Application Insights
```python
# In Streamlit app
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string="InstrumentationKey=your-key"))

# Log query executions
logger.info(f"Query executed: {user_query}", extra={"custom_dimensions": {"sql": sql_query, "rows": len(df)}})
```

### Container Monitoring
```bash
# Enable container insights
az monitor log-analytics workspace create --resource-group sports-betting-rg --workspace-name sports-betting-logs

# Configure container groups to send logs
```

## 💰 Cost Estimation (Monthly)

### Development Environment
- **App Service B1:** $13.14
- **PostgreSQL B_Gen5_1:** $24.82
- **Container Instances:** $10-20 (depending on usage)
- **Key Vault:** $3.00
- **Storage/Networking:** $5-10
- **Total:** ~$55-70/month

### Production Environment
- **App Service P1V3:** $73.00
- **PostgreSQL GP_Gen5_2:** $162.77
- **Container Instances:** $50-100
- **Application Insights:** $15-30
- **Key Vault:** $3.00
- **Storage/Networking:** $20-30
- **Total:** ~$320-400/month

## 🚀 Deployment Steps

### Phase 1: Infrastructure Setup
1. Create Resource Group
2. Deploy PostgreSQL database
3. Create Key Vault and add secrets
4. Create Container Registry
5. Set up managed identities and permissions

### Phase 2: Database Initialization
1. Run schema initialization container
2. Populate reference data (teams, sports, bookmakers)
3. Backfill historical data (2023-2024 seasons)
4. Verify data integrity

### Phase 3: Application Deployment
1. Build and push Streamlit app to App Service
2. Configure environment variables and Key Vault references
3. Test database connectivity and Claude API integration
4. Deploy scheduled data collection containers

### Phase 4: Monitoring & Optimization
1. Set up Application Insights dashboards
2. Configure alerts for failures and performance issues
3. Monitor API usage and costs
4. Optimize container scheduling based on sports seasons

## 📋 Maintenance Tasks

### Daily
- Monitor data collection container executions
- Check API credit usage
- Review application performance metrics

### Weekly
- Verify data quality and completeness
- Review and optimize database performance
- Check for failed scheduled jobs

### Monthly
- Review costs and optimize resources
- Update historical data collection for new seasons
- Security review and dependency updates

## 🔄 Disaster Recovery

### Database Backup Strategy
- **Automated Backups:** 7-day retention with geo-redundancy
- **Point-in-time Restore:** Available for last 35 days
- **Manual Snapshots:** Before major data loads or schema changes

### Application Backup
- **Source Code:** Git repository with CI/CD pipeline
- **Configuration:** Infrastructure as Code (ARM templates/Terraform)
- **Container Images:** Stored in Azure Container Registry with multiple tags

### Recovery Procedures
1. **Database Failure:** Restore from geo-redundant backup
2. **App Service Failure:** Redeploy from container registry
3. **Data Collection Failure:** Re-run missed collections from API
4. **Complete Disaster:** Rebuild infrastructure from IaC templates

---

## 📞 Next Steps

1. **Resource Provisioning:** Create Azure resources following this plan
2. **CI/CD Pipeline:** Set up automated deployment from Git repository
3. **Testing:** Deploy to development environment and test all components
4. **Production Migration:** Execute phased production deployment
5. **Documentation:** Create operational runbooks and troubleshooting guides

This deployment plan provides a scalable, secure, and cost-effective solution for hosting the Sports Betting Analytics Platform on Azure with automated data collection and robust monitoring.