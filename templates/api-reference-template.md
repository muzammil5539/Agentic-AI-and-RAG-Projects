# API Reference: [Project Name]

## Base URL

```
Production:  https://api.[project].com/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All API requests require an API key in the header:

```
Authorization: Bearer <your-api-key>
```

## Rate Limits

| Plan | Requests/min | Requests/day |
|------|-------------|--------------|
| Free | 10 | 100 |
| Pro | 60 | 5,000 |
| Enterprise | 300 | Unlimited |

## Response Format

All responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "request_id": "req_abc123",
    "latency_ms": 245,
    "tokens_used": 150
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Human-readable error description",
    "details": { ... }
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Invalid or missing API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Endpoints

### POST /[resource]

[Description of what this endpoint does]

**Request Body:**

```json
{
  "field1": "string (required) - Description",
  "field2": 42,
  "options": {
    "option1": true,
    "option2": "value"
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "res_abc123",
    "result": "...",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/[resource] \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "field1": "value",
    "field2": 42
  }'
```

---

### GET /[resource]/{id}

[Description]

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Resource identifier |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include` | string | — | Comma-separated fields to include |

**Response:**

```json
{
  "success": true,
  "data": { ... }
}
```

---

### GET /[resource]

[Description - list endpoint]

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |
| `sort` | string | created_at | Sort field |
| `order` | string | desc | Sort order (asc/desc) |

**Response:**

```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

---

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=<api-key>');
```

### Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `message` | Client → Server | Send a message |
| `response` | Server → Client | Receive response chunk |
| `done` | Server → Client | Stream complete |
| `error` | Server → Client | Error occurred |

### Message Format

```json
{
  "type": "message",
  "payload": {
    "content": "User message here",
    "session_id": "sess_abc123"
  }
}
```

---

## SDKs

### Python

```python
from project_sdk import Client

client = Client(api_key="your-key")
result = client.process(input="Hello")
```

### JavaScript

```javascript
import { Client } from '@project/sdk';

const client = new Client({ apiKey: 'your-key' });
const result = await client.process({ input: 'Hello' });
```
