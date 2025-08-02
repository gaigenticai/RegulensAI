# Risk Management Service - Monte Carlo Simulation API

## Endpoint Information

**URL**: `/api/v1/risk/simulation/monte-carlo`  
**Method**: `POST`  
**Service**: Risk Management Service  
**Port**: 8082  

## Description

Executes Monte Carlo simulation for portfolio risk analysis, calculating Value at Risk (VaR), Expected Shortfall (ES), and other risk metrics using stochastic modeling techniques. Supports multiple asset classes and correlation structures.

## Authentication

**Required**: Yes  
**Type**: Bearer Token  
**Header**: `Authorization: Bearer <jwt_token>`

## Request Schema

### Headers
```
Content-Type: application/json
Authorization: Bearer <jwt_token>
X-Request-ID: <unique_request_id>
X-Simulation-Priority: <LOW|MEDIUM|HIGH>
```

### Request Body
```json
{
  "simulation_id": "uuid",
  "portfolio_id": "uuid",
  "simulation_parameters": {
    "iterations": "number",
    "time_horizon": "number",
    "confidence_levels": ["number"],
    "random_seed": "number",
    "simulation_method": "string"
  },
  "portfolio_data": {
    "positions": [
      {
        "asset_id": "string",
        "asset_type": "string",
        "quantity": "number",
        "current_price": "number",
        "currency": "string",
        "weight": "number"
      }
    ],
    "total_value": "number",
    "base_currency": "string"
  },
  "risk_factors": {
    "market_data": {
      "volatilities": "object",
      "correlations": "object",
      "interest_rates": "object"
    },
    "scenario_adjustments": {
      "stress_factors": "object",
      "shock_scenarios": ["object"]
    }
  },
  "model_parameters": {
    "distribution_type": "string",
    "mean_reversion": "boolean",
    "jump_diffusion": "boolean",
    "stochastic_volatility": "boolean"
  },
  "output_preferences": {
    "include_paths": "boolean",
    "include_statistics": "boolean",
    "export_format": "string"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `simulation_id` | UUID | No | Optional identifier for tracking simulation |
| `portfolio_id` | UUID | Yes | Unique identifier for the portfolio |
| `simulation_parameters.iterations` | Number | Yes | Number of Monte Carlo iterations (1,000 - 1,000,000) |
| `simulation_parameters.time_horizon` | Number | Yes | Time horizon in days |
| `simulation_parameters.confidence_levels` | Array | Yes | Confidence levels for VaR calculation (e.g., [0.95, 0.99]) |
| `simulation_parameters.random_seed` | Number | No | Seed for reproducible results |
| `simulation_parameters.simulation_method` | String | Yes | Method: "STANDARD", "ANTITHETIC", "QUASI_RANDOM" |
| `portfolio_data.positions` | Array | Yes | Array of portfolio positions |
| `portfolio_data.positions[].asset_id` | String | Yes | Unique asset identifier |
| `portfolio_data.positions[].asset_type` | String | Yes | Type: "EQUITY", "BOND", "COMMODITY", "FX", "DERIVATIVE" |
| `portfolio_data.positions[].quantity` | Number | Yes | Position quantity |
| `portfolio_data.positions[].current_price` | Number | Yes | Current market price |
| `portfolio_data.total_value` | Number | Yes | Total portfolio value |
| `risk_factors.market_data.volatilities` | Object | Yes | Asset volatility parameters |
| `risk_factors.market_data.correlations` | Object | Yes | Correlation matrix between assets |
| `model_parameters.distribution_type` | String | Yes | Distribution: "NORMAL", "T_DISTRIBUTION", "SKEWED_T" |

## Response Schema

### Success Response (200 OK)
```json
{
  "success": true,
  "data": {
    "simulation_id": "uuid",
    "portfolio_id": "uuid",
    "execution_summary": {
      "iterations_completed": "number",
      "execution_time_seconds": "number",
      "convergence_achieved": "boolean",
      "random_seed_used": "number"
    },
    "risk_metrics": {
      "value_at_risk": {
        "var_95": "number",
        "var_99": "number",
        "var_99_9": "number"
      },
      "expected_shortfall": {
        "es_95": "number",
        "es_99": "number",
        "es_99_9": "number"
      },
      "portfolio_statistics": {
        "expected_return": "number",
        "portfolio_volatility": "number",
        "skewness": "number",
        "kurtosis": "number",
        "maximum_drawdown": "number"
      }
    },
    "distribution_analysis": {
      "percentiles": {
        "p1": "number",
        "p5": "number",
        "p10": "number",
        "p25": "number",
        "p50": "number",
        "p75": "number",
        "p90": "number",
        "p95": "number",
        "p99": "number"
      },
      "tail_statistics": {
        "worst_case_loss": "number",
        "best_case_gain": "number",
        "tail_expectation": "number"
      }
    },
    "scenario_analysis": [
      {
        "scenario_name": "string",
        "probability": "number",
        "portfolio_impact": "number",
        "key_drivers": ["string"]
      }
    ],
    "model_validation": {
      "backtesting_results": {
        "hit_ratio": "number",
        "independence_test": "string",
        "coverage_test": "string"
      },
      "model_diagnostics": {
        "convergence_metrics": "object",
        "stability_indicators": "object"
      }
    },
    "simulation_paths": {
      "sample_paths": ["array"],
      "path_statistics": "object"
    },
    "recommendations": [
      {
        "type": "string",
        "priority": "string",
        "description": "string",
        "impact": "string"
      }
    ],
    "created_at": "string (ISO 8601)",
    "expires_at": "string (ISO 8601)"
  },
  "message": "Monte Carlo simulation completed successfully"
}
```

### Error Response (400 Bad Request)
```json
{
  "success": false,
  "error": "Invalid simulation parameters",
  "details": {
    "field_errors": [
      {
        "field": "string",
        "message": "string"
      }
    ]
  }
}
```

## Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `execution_summary.iterations_completed` | Number | Actual number of iterations completed |
| `execution_summary.convergence_achieved` | Boolean | Whether simulation converged to stable results |
| `risk_metrics.value_at_risk.var_95` | Number | 95% Value at Risk in base currency |
| `risk_metrics.expected_shortfall.es_95` | Number | 95% Expected Shortfall (Conditional VaR) |
| `portfolio_statistics.expected_return` | Number | Expected portfolio return over time horizon |
| `portfolio_statistics.portfolio_volatility` | Number | Portfolio volatility (standard deviation) |
| `distribution_analysis.percentiles` | Object | Portfolio return distribution percentiles |
| `tail_statistics.worst_case_loss` | Number | Maximum simulated loss |
| `model_validation.backtesting_results.hit_ratio` | Number | Backtesting hit ratio for model validation |
| `simulation_paths.sample_paths` | Array | Sample simulation paths (if requested) |

## Example Usage

### cURL Example
```bash
curl -X POST "https://api.regulateai.com/api/v1/risk/simulation/monte-carlo" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Request-ID: req_mc_simulation_123" \
  -H "X-Simulation-Priority: HIGH" \
  -d '{
    "portfolio_id": "port_550e8400-e29b-41d4-a716-446655440000",
    "simulation_parameters": {
      "iterations": 100000,
      "time_horizon": 252,
      "confidence_levels": [0.95, 0.99, 0.999],
      "simulation_method": "ANTITHETIC"
    },
    "portfolio_data": {
      "positions": [
        {
          "asset_id": "AAPL",
          "asset_type": "EQUITY",
          "quantity": 1000,
          "current_price": 150.00,
          "currency": "USD",
          "weight": 0.3
        },
        {
          "asset_id": "GOOGL",
          "asset_type": "EQUITY", 
          "quantity": 500,
          "current_price": 2800.00,
          "currency": "USD",
          "weight": 0.7
        }
      ],
      "total_value": 1550000.00,
      "base_currency": "USD"
    },
    "risk_factors": {
      "market_data": {
        "volatilities": {
          "AAPL": 0.25,
          "GOOGL": 0.30
        },
        "correlations": {
          "AAPL_GOOGL": 0.65
        }
      }
    },
    "model_parameters": {
      "distribution_type": "NORMAL",
      "mean_reversion": false,
      "jump_diffusion": false,
      "stochastic_volatility": false
    },
    "output_preferences": {
      "include_paths": false,
      "include_statistics": true,
      "export_format": "JSON"
    }
  }'
```

### R Example
```r
library(httr)
library(jsonlite)

url <- "https://api.regulateai.com/api/v1/risk/simulation/monte-carlo"
headers <- add_headers(
  `Content-Type` = "application/json",
  `Authorization` = paste("Bearer", token),
  `X-Request-ID` = "req_mc_r_analysis"
)

payload <- list(
  portfolio_id = "port_550e8400-e29b-41d4-a716-446655440000",
  simulation_parameters = list(
    iterations = 50000,
    time_horizon = 252,
    confidence_levels = c(0.95, 0.99),
    simulation_method = "STANDARD"
  ),
  portfolio_data = list(
    positions = list(
      list(
        asset_id = "SPY",
        asset_type = "ETF",
        quantity = 10000,
        current_price = 400.00,
        currency = "USD",
        weight = 1.0
      )
    ),
    total_value = 4000000.00,
    base_currency = "USD"
  ),
  risk_factors = list(
    market_data = list(
      volatilities = list(SPY = 0.16)
    )
  ),
  model_parameters = list(
    distribution_type = "NORMAL"
  )
)

response <- POST(url, headers, body = toJSON(payload, auto_unbox = TRUE))
result <- fromJSON(content(response, "text"))

if (result$success) {
  var_95 <- result$data$risk_metrics$value_at_risk$var_95
  es_95 <- result$data$risk_metrics$expected_shortfall$es_95
  cat("95% VaR:", var_95, "\n95% ES:", es_95)
}
```

## Performance Specifications

- **Processing Time**: 
  - 10,000 iterations: < 5 seconds
  - 100,000 iterations: < 30 seconds
  - 1,000,000 iterations: < 5 minutes
- **Concurrent Simulations**: Up to 10 simultaneous simulations per account
- **Memory Usage**: Optimized for large portfolios (up to 10,000 positions)

## Rate Limiting

- **Rate Limit**: 50 simulations per hour per API key
- **Concurrent Limit**: 5 active simulations per account
- **Priority Queue**: HIGH priority requests processed first

## Model Features

1. **Advanced Modeling**:
   - Multiple probability distributions
   - Stochastic volatility models
   - Jump-diffusion processes
   - Mean reversion capabilities

2. **Correlation Handling**:
   - Full correlation matrix support
   - Dynamic correlation modeling
   - Copula-based dependence structures

3. **Validation & Testing**:
   - Automated backtesting
   - Model convergence checks
   - Statistical validation tests

## Use Cases

- **Portfolio Risk Assessment**: Calculate VaR and ES for investment portfolios
- **Regulatory Capital**: Meet Basel III and Solvency II requirements
- **Stress Testing**: Analyze portfolio performance under adverse scenarios
- **Risk Budgeting**: Allocate risk across portfolio components
- **Model Validation**: Validate other risk models through simulation

## Related Endpoints

- `GET /api/v1/risk/simulation/{simulation_id}` - Get simulation results
- `POST /api/v1/risk/simulation/stress-test` - Run stress test scenarios
- `GET /api/v1/risk/portfolio/{portfolio_id}/metrics` - Get portfolio risk metrics
- `POST /api/v1/risk/backtesting/validate` - Validate risk models
