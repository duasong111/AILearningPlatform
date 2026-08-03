from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plan", "0004_learningplan_expected_completion_time_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="learningplan",
            name="state",
            field=models.CharField(
                choices=[
                    ("pending", "待执行"),
                    ("running", "执行中"),
                    ("success", "已完成"),
                    ("failed", "已失败"),
                    ("skipped", "已跳过"),
                ],
                default="pending",
                max_length=20,
                verbose_name="计划状态",
            ),
        ),
    ]
