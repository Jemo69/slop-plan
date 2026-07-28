from tortoise import migrations, fields
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    initial = False

    operations = [
        ops.AddField(
            model_name='project',
            name='is_archived',
            field=fields.BooleanField(default=False),
        ),
    ]