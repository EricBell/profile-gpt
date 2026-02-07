# OpenAI Usage API Integration

## Overview

ProfileGPT now includes integration with OpenAI's Usage API, allowing you to fetch official usage data directly from OpenAI and reconcile it with your local tracking logs.

## Features

### 1. Official Usage Data from OpenAI
- Fetch historical usage data from OpenAI's `/v1/organization/usage/completions` endpoint
- View aggregated token usage by date
- Compare against your local tracking for accuracy

### 2. Reconciliation Dashboard
- Side-by-side comparison of local vs OpenAI data
- Automatic difference calculation (tokens, requests, costs)
- Reconciliation status indicator (within 5% = reconciled)
- Visual diff display with percentage differences

### 3. Data Validation
- Verify accuracy of local usage tracking
- Identify discrepancies in token counts
- Validate cost calculations
- Ensure billing alignment

## How It Works

### Data Flow

```
┌─────────────────┐
│   Your App      │
│  (ProfileGPT)   │
└────────┬────────┘
         │
         ├─> Local logs (usage_tracking.ndjson)
         │   └─> Per-request token tracking
         │
         └─> OpenAI API calls
                 │
                 ▼
         ┌───────────────┐
         │  OpenAI API   │
         │   (servers)   │
         └───────┬───────┘
                 │
                 └─> Usage API endpoint
                     └─> Aggregated usage data
```

When you visit the reconciliation dashboard:
1. Local usage logs are parsed and aggregated
2. OpenAI Usage API is called to fetch official data
3. The two datasets are compared
4. Differences are calculated and displayed

## Usage API Endpoint

**Endpoint:** `GET https://api.openai.com/v1/organization/usage/completions`

**Authentication:** Uses your `OPENAI_API_KEY`

**Parameters:**
- `start_time` (required) - Unix timestamp (seconds)
- `end_time` (optional) - Unix timestamp (seconds)
- `bucket_width` (optional) - Time bucket size: `1m`, `1h`, or `1d` (default: `1d`)

**Response Format:**
```json
{
  "object": "page",
  "data": [
    {
      "aggregation_timestamp": 1738886400,
      "results": [
        {
          "input_tokens": 12500,
          "output_tokens": 8300,
          "num_model_requests": 45
        }
      ]
    }
  ]
}
```

## Accessing the Usage API Dashboard

### URL
`https://your-domain.com/usage-api?key=YOUR_ADMIN_KEY`

### Required Environment Variables
- `ADMIN_RESET_KEY` - Admin authentication key
- `OPENAI_API_KEY` - OpenAI API key with organization access

### Date Range Selection
By default, shows last 7 days. You can customize:
- **Start Date** - Beginning of date range (YYYY-MM-DD)
- **End Date** - End of date range (YYYY-MM-DD)

### Example URLs
```
# Last 7 days (default)
/usage-api?key=YOUR_KEY

# Specific date range
/usage-api?key=YOUR_KEY&start_date=2026-02-01&end_date=2026-02-07

# Export as JSON
/usage-api?key=YOUR_KEY&format=json
```

## Understanding the Dashboard

### Reconciliation Status
- **✓ Reconciled (within 5%)** - Local tracking matches OpenAI within acceptable tolerance
- **⚠ Mismatch Detected** - Significant difference found, review discrepancies

### Comparison Metrics

**Token Difference:**
- Shows difference in total tokens tracked
- Positive = Local tracking shows more tokens
- Negative = OpenAI shows more tokens

**Request Difference:**
- Shows difference in number of API calls
- Helps identify missing or extra logs

**Cost Difference:**
- Shows difference in estimated costs
- Important for budget reconciliation

### Color Coding
- **Green (positive)** - Local tracking is higher
- **Red (negative)** - OpenAI data is higher
- **Gray (neutral)** - No difference

## Why Differences Occur

Small differences (< 5%) are normal due to:

1. **Timing Differences**
   - Local logs recorded in real-time
   - OpenAI aggregates data in batches
   - Timezone/timestamp conversion

2. **Aggregation Methods**
   - OpenAI buckets data by time periods
   - Local tracking is per-request granular
   - Rounding differences in aggregation

3. **Cost Calculation**
   - Local uses published pricing rates
   - OpenAI may have different internal rates
   - Promotional credits or discounts

4. **Network Issues**
   - Failed requests may not be logged locally
   - OpenAI always records all attempts
   - Retry logic may cause duplicates

## Troubleshooting

### Error: "OpenAI Usage API not available"

**Cause:** Your API key doesn't have organization-level access.

**Solution:**
- The Usage API requires an organization API key
- Personal API keys may not have access
- Contact OpenAI support to enable organization features

### Error: "OPENAI_API_KEY not configured"

**Cause:** Environment variable not set.

**Solution:**
```bash
# Add to .env file
OPENAI_API_KEY=sk-proj-...
```

### Large Discrepancies (> 5%)

**Possible causes:**
1. **Missing local logs** - Check if logs were rotated or deleted
2. **Multiple API keys** - Using different keys than what's being tracked
3. **Different time ranges** - Verify date filters match
4. **Development vs Production** - Ensure comparing same environment

**Investigation steps:**
1. Check `logs/usage_tracking.ndjson` exists and has data
2. Verify date range covers the same period
3. Review `/usage-stats` for local data sanity check
4. Compare request counts first (easier to validate)

## Programmatic Access

You can also use the reconciliation functions in your own scripts:

```python
from usage_tracker import fetch_openai_usage, parse_openai_usage_response, compare_usage
from usage_tracker import parse_usage_logs, calculate_usage_stats

# Fetch from OpenAI
openai_response = fetch_openai_usage(
    api_key='sk-proj-...',
    start_date='2026-02-01',
    end_date='2026-02-07',
    bucket_width='1d'
)
openai_stats = parse_openai_usage_response(openai_response)

# Load local data
local_records = parse_usage_logs('./logs', start_date='2026-02-01', end_date='2026-02-07')
local_stats = calculate_usage_stats(local_records)

# Compare
comparison = compare_usage(local_stats, openai_stats)

print(f"Reconciled: {comparison['reconciled']}")
print(f"Token difference: {comparison['difference']['tokens']} ({comparison['difference']['tokens_pct']:.1f}%)")
print(f"Cost difference: ${comparison['difference']['cost']:.4f}")
```

## Use Cases

### 1. Monthly Reconciliation
At the end of each month, reconcile usage with OpenAI's billing:

```python
from datetime import datetime, timedelta

# Get last month
last_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
last_month_end = datetime.now().replace(day=1).strftime('%Y-%m-%d')

# Compare
# Visit: /usage-api?key=KEY&start_date={last_month_start}&end_date={last_month_end}
```

### 2. Validate Tracking Accuracy
After deploying the usage tracking feature, verify it's working:

```python
# Check last 24 hours
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
today = datetime.now().strftime('%Y-%m-%d')

# Should be within 5%
# Visit: /usage-api?key=KEY&start_date={yesterday}&end_date={today}
```

### 3. Audit for Billing Disputes
If OpenAI's invoice seems high, use reconciliation to audit:

1. Check the disputed billing period
2. Export both datasets as JSON
3. Compare line-by-line for discrepancies
4. Provide evidence to OpenAI support if needed

### 4. Multi-Environment Tracking
Compare production vs staging usage:

```python
# Production logs
prod_records = parse_usage_logs('./logs/production')
prod_stats = calculate_usage_stats(prod_records)

# Staging logs
staging_records = parse_usage_logs('./logs/staging')
staging_stats = calculate_usage_stats(staging_records)

# OpenAI shows combined usage - verify total
openai_stats = fetch_openai_usage(...)
# prod + staging should match openai
```

## API Rate Limits

The OpenAI Usage API has rate limits:
- **Requests per minute:** 60 (typical)
- **Daily limit:** Not specified

**Best practices:**
- Cache results for frequently accessed date ranges
- Don't call on every page load
- Use manual refresh or scheduled jobs

## Cost Considerations

**Usage API calls are FREE** - They don't count toward token usage.

However, they do count toward rate limits, so:
- Don't spam the endpoint
- Use reasonable date ranges
- Cache results when possible

## Data Retention

**OpenAI Usage API:**
- Retains data for billing purposes
- Typically 90+ days available
- Check OpenAI docs for exact retention policy

**Local Tracking:**
- Unlimited retention (stored locally)
- Controlled by you (can archive/delete as needed)
- Recommend keeping 12+ months for accounting

## Security Considerations

1. **API Key Protection**
   - Usage API uses same key as regular API
   - Has access to organization usage data
   - Keep `OPENAI_API_KEY` secure

2. **Admin Access**
   - Reconciliation dashboard requires `ADMIN_RESET_KEY`
   - Shows sensitive billing information
   - Restrict access to finance/admin users

3. **Data Privacy**
   - OpenAI Usage API only shows aggregated data
   - Does not expose actual prompt/completion content
   - Safe for financial reconciliation

## Future Enhancements

Potential improvements:

1. **Automated Reconciliation**
   - Schedule daily reconciliation checks
   - Email alerts on significant mismatches
   - Automatic issue detection

2. **Historical Trends**
   - Track reconciliation accuracy over time
   - Identify patterns in discrepancies
   - Improve logging based on mismatches

3. **Multi-API Support**
   - Add embeddings, audio, images endpoints
   - Comprehensive usage tracking across all APIs
   - Unified reconciliation view

4. **Cost Attribution**
   - Break down costs by project/department
   - Allocate usage to specific teams
   - Charge-back reporting

## References

- [OpenAI Usage API Documentation](https://platform.openai.com/docs/api-reference/usage)
- [How to use the Usage API and Cost API - OpenAI Cookbook](https://cookbook.openai.com/examples/completions_usage_api)
- [OpenAI Pricing](https://openai.com/api/pricing/)

## Version History

- **v0.14.0** - Initial release of OpenAI Usage API integration
