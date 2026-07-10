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
    is_approved = fields.BooleanField(default=False)
    approved_at = fields.DatetimeField(null=True)
    approved_by = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "plans"

    def __str__(self):
        return self.title
