from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from json import dumps, loads
from tortoise.fields.base import OnDelete
from uuid import uuid4
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='User',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('email', fields.CharField(unique=True, db_index=True, max_length=255)),
                ('password_hash', fields.CharField(null=True, max_length=255)),
                ('api_key', fields.CharField(unique=True, db_index=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'users', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Project',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('models.User', source_field='user_id', db_constraint=True, to_field='id', related_name='projects', on_delete=OnDelete.CASCADE)),
                ('name', fields.CharField(max_length=255)),
                ('description', fields.TextField(null=True, unique=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'projects', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Plan',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('project', fields.ForeignKeyField('models.Project', source_field='project_id', db_constraint=True, to_field='id', related_name='plans', on_delete=OnDelete.CASCADE)),
                ('title', fields.CharField(max_length=255)),
                ('slug', fields.CharField(unique=True, db_index=True, max_length=255)),
                ('html_content', fields.TextField(unique=False)),
                ('frontmatter', fields.JSONField(null=True, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('is_public', fields.BooleanField(default=False)),
                ('is_approved', fields.BooleanField(default=False)),
                ('approved_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('approved_by', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'plans', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='PlanPin',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('models.User', source_field='user_id', db_constraint=True, to_field='id', related_name='plan_pins', on_delete=OnDelete.CASCADE)),
                ('plan', fields.ForeignKeyField('models.Plan', source_field='plan_id', db_constraint=True, to_field='id', related_name='pins', on_delete=OnDelete.CASCADE)),
                ('pinned_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'plan_pins', 'app': 'models', 'unique_together': (('user', 'plan'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='ProjectPin',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('user', fields.ForeignKeyField('models.User', source_field='user_id', db_constraint=True, to_field='id', related_name='project_pins', on_delete=OnDelete.CASCADE)),
                ('project', fields.ForeignKeyField('models.Project', source_field='project_id', db_constraint=True, to_field='id', related_name='pins', on_delete=OnDelete.CASCADE)),
                ('pinned_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'project_pins', 'app': 'models', 'unique_together': (('user', 'project'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
