# Plan CLI

CLI tool for HTML Plan Service - Create, manage, and share HTML plans.

## Installation

```bash
cd cli
uv sync
```

## Usage

### Authentication

```bash
# Register a new account
plan auth init --email your@email.com

# Login to existing account
plan auth login --email your@email.com
```

### Plans

```bash
# Create a plan
plan plans create --project <project-id> --title "My Plan" --html plan.html

# List all plans
plan plans list

# List plans for a project
plan plans list --project <project-id>

# Get plan details
plan plans get <plan-id>

# Update a plan
plan plans update <plan-id> --html updated.html

# Delete a plan
plan plans delete <plan-id>

# Publish a plan (make public)
plan plans publish <plan-id>

# Unpublish a plan (make private)
plan plans unpublish <plan-id>
```

## Configuration

The CLI stores configuration in `~/.plan-cli/config.json`:

```json
{
  "api_url": "http://localhost:8000",
  "api_key": "your-api-key"
}
```

## Frontmatter Support

HTML files can include YAML frontmatter:

```html
---
title: My Plan Title
description: Brief description
tags: [architecture, api-design]
visibility: public
---
<!DOCTYPE html>
<html>
...
</html>
```

The CLI will extract metadata from frontmatter and use it when creating plans.
