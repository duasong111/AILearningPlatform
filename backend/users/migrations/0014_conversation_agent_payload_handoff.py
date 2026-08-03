from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_message_meta"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="agent_payload",
            field=models.JSONField(blank=True, default=dict, help_text="当前 agent 的结构化配置，不同 agent 使用不同字段", verbose_name="agent 配置"),
        ),
        migrations.AddField(
            model_name="conversation",
            name="handoff",
            field=models.JSONField(blank=True, default=dict, help_text="上一个 agent 交接给当前会话的结构化信息", verbose_name="agent 交接信息"),
        ),
    ]
