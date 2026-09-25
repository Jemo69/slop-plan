import uuid
from tortoise import fields, models


class User(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    email = fields.CharField(max_length=255, unique=True, index=True)
    password_hash = fields.CharField(max_length=255, null=True)
    api_key = fields.CharField(max_length=255, unique=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def __str__(self):
        return self.email


class Project(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user = fields.ForeignKeyField("models.User", related_name="projects", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    is_archived = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "projects"

    def __str__(self):
        return self.name


class Plan(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    project = fields.ForeignKeyField("models.Project", related_name="plans", on_delete=fields.CASCADE)
    title = fields.CharField(max_length=255)
    slug = fields.CharField(max_length=255, unique=True, index=True)
    html_content = fields.TextField()
    frontmatter = fields.JSONField(null=True)
    is_public = fields.BooleanField(default=False)
    is_archived = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "plans"

    def __str__(self):
        return self.title


class PlanVersion(models.Model):
    """Immutable snapshot of a plan's content at a point in time.

    Versions are numbered per-plan starting at 1. A new version is written
    *before* an update is applied, so it always holds the state that the
    update replaced. `note` is an optional human label for manual snapshots.
    """

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    plan = fields.ForeignKeyField("models.Plan", related_name="versions", on_delete=fields.CASCADE)
    version = fields.IntField()
    title = fields.CharField(max_length=255)
    html_content = fields.TextField()
    frontmatter = fields.JSONField(null=True)
    note = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "plan_versions"
        unique_together = (("plan", "version"),)

    def __str__(self):
        return f"{self.plan} v{self.version}"


class ProjectPin(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user = fields.ForeignKeyField("models.User", related_name="project_pins", on_delete=fields.CASCADE)
    project = fields.ForeignKeyField("models.Project", related_name="pins", on_delete=fields.CASCADE)
    pinned_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "project_pins"
        unique_together = ("user", "project")

    def __str__(self):
        return f"{self.user} pinned {self.project}"


class PlanPin(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user = fields.ForeignKeyField("models.User", related_name="plan_pins", on_delete=fields.CASCADE)
    plan = fields.ForeignKeyField("models.Plan", related_name="pins", on_delete=fields.CASCADE)
    pinned_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "plan_pins"
        unique_together = ("user", "plan")

    def __str__(self):
        return f"{self.user} pinned {self.plan}"
