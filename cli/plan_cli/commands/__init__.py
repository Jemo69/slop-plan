from plan_cli.commands.auth import app as auth_app
from plan_cli.commands.plans import app as plans_app
from plan_cli.commands.projects import app as projects_app
from plan_cli.commands.config_cmd import app as config_app

__all__ = ["auth_app", "plans_app", "projects_app", "config_app"]
