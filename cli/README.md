# Plan CLI

CLI tool for HTML Plan Service - Create, manage, and share HTML plans.

## Installation

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/Jemo69/html-planner-server/main/cli/install.sh | bash
```

Or manually:

```bash
cd cli
uv sync
```

## Usage

### Configuration

```bash
# Show current config
plan config show

# Set API URL
plan config set --api-url https://html-planner-server.fly.dev

# Get current API URL
plan config get
```

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
