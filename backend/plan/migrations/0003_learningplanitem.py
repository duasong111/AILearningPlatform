from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("plan", "0002_learningplan_difficulty"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningPlanItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_id", models.CharField(max_length=32, verbose_name="知识点 ID")),
                ("node_name", models.CharField(max_length=100, verbose_name="知识点名称")),
                ("node_type", models.CharField(blank=True, default="", max_length=32, verbose_name="知识点类型")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="计划项顺序")),
                ("difficulty", models.PositiveSmallIntegerField(default=1, verbose_name="节点难度")),
                ("expected_minutes", models.PositiveIntegerField(default=30, verbose_name="预计耗时（分钟）")),
                ("expected_completion_time", models.DateTimeField(blank=True, null=True, verbose_name="预期完成时间")),
                ("actual_completion_time", models.DateTimeField(blank=True, null=True, verbose_name="实际完成时间")),
                ("state", models.CharField(
                    choices=[
                        ("pending", "待执行"),
                        ("running", "执行中"),
                        ("success", "已完成"),
                        ("failed", "已失败"),
                        ("skipped", "已跳过"),
                    ],
                    default="pending",
                    max_length=20,
                    verbose_name="项状态",
                )),
                ("completed", models.BooleanField(default=False, verbose_name="是否完成")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("plan", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="items",
                    to="plan.learningplan",
                )),
            ],
            options={
                "verbose_name": "学习计划项",
                "verbose_name_plural": "学习计划项",
                "ordering": ["plan_id", "order", "id"],
                "unique_together": {("plan", "node_id")},
            },
        ),
    ]