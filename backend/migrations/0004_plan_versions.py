from tortoise import migrations, fields
from tortoise.migrations import operations as ops
import functools
from json import dumps, loads
from tortoise.fields.base import OnDelete
from uuid import uuid4


class Migration(migrations.Migration):
    initial = False

    operations = [
        ops.CreateModel(
            name='PlanVersion',
            fields=[
                ('id', fields.UUIDField(primary_key=True, default=uuid4, unique=True, db_index=True)),
                ('plan', fields.ForeignKeyField('models.Plan', source_field='plan_id', db_constraint=True, to_field='id', related_name='versions', on_delete=OnDelete.CASCADE)),
                ('version', fields.IntField(default=0)),
                ('title', fields.CharField(max_length=255)),
                ('html_content', fields.TextField(unique=False)),
                ('frontmatter', fields.JSONField(null=True, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('note', fields.CharField(null=True, max_length=255)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={'table': 'plan_versions', 'app': 'models', 'unique_together': (('plan', 'version'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
