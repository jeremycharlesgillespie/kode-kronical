# AWS DynamoDB Setup for KodeKronical

## Installation with AWS Support

First, ensure you have the necessary dependencies:

```bash
# Install kode-kronical with AWS dependencies
pip install kode-kronical-jg boto3

# Or install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kode-kronical-jg boto3
```

## Required AWS Role/Policy

To allow KodeKronical to upload timing data to DynamoDB, you need to create an IAM role or user with the following permissions:

### IAM Policy JSON

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:DescribeTable",
                "dynamodb:CreateTable"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/kode-kronical-data"
            ]
        }
    ]
}
```

### Setup Options

#### Option 1: IAM User (Recommended for development)

1. Create an IAM user in AWS Console
2. Attach the policy above to the user
3. Create access keys for the user
4. Configure AWS credentials locally:

```bash
# Option A: AWS CLI
aws configure
# Enter your Access Key ID, Secret Access Key, and region (us-east-1)

# Option B: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_DEFAULT_REGION=us-east-1

# Option C: AWS credentials file
# Create ~/.aws/credentials with:
[default]
aws_access_key_id = your_access_key_id
aws_secret_access_key = your_secret_access_key
region = us-east-1
```

#### Option 2: IAM Role (Recommended for production/EC2)

1. Create an IAM role in AWS Console
2. Attach the policy above to the role
3. Attach the role to your EC2 instance or application

### DynamoDB Table Structure

The `kode-kronical-data` table stores the following data:

- **id** (Number, Primary Key): Unique microsecond timestamp
- **session_id** (String): UUID for each KodeKronical session
- **timestamp** (Number): Unix timestamp when data was uploaded
- **hostname** (String): Machine hostname
- **data** (String): Complete JSON timing results
- **total_calls** (Number): Total function calls in session
- **total_wall_time** (Number): Total wall time in seconds
- **total_cpu_time** (Number): Total CPU time in seconds

### Configuration Options

Configure KodeKronical's DynamoDB behavior using a `.kode-kronical.yaml` configuration file:

```yaml
kode_kronical:
  enabled: true

# For local development (no AWS required)
local:
  enabled: true  # This disables AWS uploads
  data_dir: "./perf_data"
  format: "json"

# For production with AWS DynamoDB
# local:
#   enabled: false

aws:
  region: "us-east-1"
  table_name: "kode-kronical-data"
  auto_create_table: true
  read_capacity: 5
  write_capacity: 5
```

You can also configure KodeKronical programmatically:

```python
from kode_kronical import KodeKronical

# Default configuration (loads .kode-kronical.yaml automatically)
perf = KodeKronical()

# Override with custom AWS settings
perf = KodeKronical({
    "aws": {
        "region": "us-east-1",
        "table_name": "my-custom-table"
    },
    "local": {"enabled": False}
})
```
