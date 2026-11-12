# Plan CLI

CLI tool for Slop Plans - Create, manage, and share HTML plans.

## Features

- Create, update, delete plans
- Publish/unpublish plans (public URL)
- Pin plans via the web dashboard

## Installation

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/Jemo69/slop-plan/main/cli/install.sh | bash
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
plan config set --api-url https://slop-plans.vercel.app

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

# Archive a plan
plan plans archive <plan-id>

# Restore an archived plan
plan plans unarchive <plan-id>
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
