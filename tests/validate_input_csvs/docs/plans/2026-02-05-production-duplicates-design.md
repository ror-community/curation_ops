# Production Duplicates Validator Design

## Overview

Integrate `on_production_duplicate_check` functionality into the CSV validation tool. The validator checks input CSV records against the live ROR API to find potential duplicate organizations already in production.

## Requirements

- **Input:** CSV file (new records only, no ROR ID)
- **API:** Live ROR API v2 (query and affiliation endpoints)
- **Matching:** 85% fuzzy threshold on names
- **Country filtering:** Require country code match (derived from GeoNames ID lookup)
- **Processing:** Parallel with 5 workers
- **GeoNames:** Required for country code lookup

## Architecture

```
validate_ror_records_input_csvs/
├── core/
│   ├── ror_api.py       # NEW: ROR API client with rate limiting
│   └── geonames.py      # NEW: GeoNames client with failure tracking
└── validators/
    └── production_duplicates.py  # NEW: The validator
```

## Component Designs

### 1. ROR API Client (`core/ror_api.py`)

```python
class RateLimiter:
    """Thread-safe rate limiter for API calls."""
    # Default: 1000 calls per 300 seconds (5 minutes)
    # Uses threading.Lock for thread safety with ThreadPoolExecutor
    # Tracks call timestamps, sleeps if limit exceeded

class RORAPIClient:
    """Client for ROR API v2 search endpoints."""

    BASE_URL = "https://api.ror.org/v2/organizations"

    def __init__(self, rate_limiter: RateLimiter = None):
        self.rate_limiter = rate_limiter or RateLimiter()

    def search_query(self, name: str) -> list[dict]:
        """Search using ?query= parameter."""

    def search_affiliation(self, name: str) -> list[dict]:
        """Search using ?affiliation= parameter."""
        # Unwraps 'organization' key from affiliation results

    def search_all(self, name: str) -> list[dict]:
        """Combines query and affiliation results, deduplicated by ROR ID."""
```

### 2. GeoNames Client (`core/geonames.py`)

```python
class GeoNamesClient:
    """Client for GeoNames API lookups with failure tracking."""

    BASE_URL = "http://api.geonames.org/getJSON"

    def __init__(self, username: str):
        self.username = username
        self._cache: dict[str, str | None] = {}  # geonames_id -> country_code
        self.lookup_failures: list[dict] = []    # Failed lookups for reporting

    def get_country_code(self, geonames_id: str, record_identifier: str = "") -> str | None:
        """Lookup country code for a GeoNames ID.

        Returns cached result if available.
        On failure, logs to lookup_failures and returns None.
        """
```

**Shared failure output:** `geonames_lookup_failures.csv`
- `geonames_id` - The ID that failed lookup
- `record_identifier` - Display name of the record
- `source_validator` - Which validator encountered the failure

This failure tracking can be shared with `address-validation` validator.

### 3. Production Duplicates Validator (`validators/production_duplicates.py`)

```python
class ProductionDuplicatesValidator(BaseValidator):
    name = "production-duplicates"
    output_filename = "production_duplicates.csv"
    output_fields = [
        "name",              # Name from input CSV that was searched
        "display_name",      # Display name of the input record
        "matched_ror_id",    # ROR ID of potential duplicate
        "matched_name",      # Name from ROR that matched
        "match_ratio",       # Fuzzy match score (85-100)
    ]
    requires_data_source = False
    requires_geonames = True
    new_records_only = True
```

**Processing logic:**

1. Initialize `RORAPIClient` with rate limiter and `GeoNamesClient` with username
2. Read CSV, parse records extracting:
   - `names.types.ror_display` (display name, used as identifier)
   - `names.types.alias` (semicolon-separated)
   - `names.types.label` (semicolon-separated)
   - `geonames_id`
3. Use `ThreadPoolExecutor(max_workers=5)` to process records in parallel
4. For each record:
   - Look up country code from geonames_id via GeoNamesClient
   - If lookup fails, log failure and skip record
   - For each name (display, aliases, labels):
     - Call `RORAPIClient.search_all(name)`
     - Filter results to those with matching country code
     - Apply 85% fuzzy matching between searched name and result names
     - Collect matches with score >= 85
5. Deduplicate results (same name + matched_ror_id pair)
6. Return findings list

**Helper functions:**

```python
def get_country_code_from_result(result: dict) -> str | None:
    """Extract country code from ROR API result."""
    # locations[0].geonames_details.country_code

def get_all_names_from_result(result: dict) -> list[str]:
    """Extract all names (ror_display, alias, label) from ROR API result."""

def parse_csv_names(row: dict) -> list[str]:
    """Extract names from CSV row."""
    # Reuse from in_release_duplicates.py
```

## Data Flow

```
CSV Input
    │
    ▼
┌─────────────────────────────────────┐
│ For each record (parallel, 5 workers)│
├─────────────────────────────────────┤
│ 1. Extract geonames_id              │
│ 2. GeoNames API → country_code      │
│    └─ On failure: log, skip record  │
│ 3. For each name:                   │
│    └─ ROR API (query + affiliation) │
│       └─ Filter by country match    │
│       └─ Fuzzy match >= 85%         │
└─────────────────────────────────────┘
    │
    ▼
Deduplicate Results
    │
    ▼
production_duplicates.csv
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| GeoNames lookup fails | Log to `geonames_lookup_failures.csv`, skip record |
| ROR API call fails | Log warning, skip that name search, continue with others |
| Invalid geonames_id | Treated as lookup failure |
| Empty names | Skip (no names to search) |
| Rate limit approached | Sleep until calls available |

## Integration Changes

### `validators/__init__.py`
```python
from .production_duplicates import ProductionDuplicatesValidator
register_validator(ProductionDuplicatesValidator())
```

### `runner.py`
- Add logic to write shared `geonames_lookup_failures.csv` at end if any validator produced failures
- Pass GeoNamesClient instance through context (or create per-validator)

### README.md
Add to validators table:
| `production-duplicates` | Checks for potential duplicates in ROR production via API search | `--geonames-user` (required) |

Add to output table:
| `production-duplicates` | `production_duplicates.csv` |

Add shared output:
| (shared) | `geonames_lookup_failures.csv` |

## Dependencies

No new dependencies required:
- `requests` - already in project
- `thefuzz` - already in project
- `concurrent.futures` - stdlib

## Testing Considerations

- Mock ROR API responses for unit tests
- Mock GeoNames API responses for unit tests
- Test rate limiter with time mocking
- Test parallel processing with small datasets
- Integration test with real APIs (optional, slow)
