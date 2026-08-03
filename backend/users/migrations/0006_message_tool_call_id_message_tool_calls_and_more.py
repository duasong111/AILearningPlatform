# Generated for LangChain tool-calling message persistence.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_add_conversation_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='tool_call_id',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='工具调用 ID'),
        ),
        migrations.AddField(
            model_name='message',
            name='tool_calls',
            field=models.JSONField(blank=True, default=list, verbose_name='LLM 决策的工具调用'),
        ),
        migrations.AddField(
            model_name='message',
            name='tool_name',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='工具名'),
        ),
        migrations.AlterField(
            model_name='message',
            name='role',
            field=models.CharField(
                choices=[
                    ('user', '用户'),
                    ('assistant', 'AI助手'),
                    ('tool', '工具返回'),
                ],
                max_length=20,
                verbose_name='角色',
            ),
        ),
    ]
