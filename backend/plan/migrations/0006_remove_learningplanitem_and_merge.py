"""删除 LearningPlanItem，将字段提升到 LearningPlan。

冲突处理：
- `difficulty` 字段在 0002 已存在为 CharField(low/medium/high) —— 重命名为 `plan_difficulty`
- `expected_completion_time` 字段在 0004 已存在 —— 不重复 AddField，加 db_index 即可
- `state` 加 db_index（替换原状态）
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plan", "0005_learningplan_state_skipped"),
    ]

    operations = [
        # 0. 先把旧的 `difficulty` CharField 重命名为 `plan_difficulty`
        #    （保留用户已有数据：low/medium/high）
        migrations.RenameField(
            model_name="learningplan",
            old_name="difficulty",
            new_name="plan_difficulty",
        ),

        # 1. 删除 LearningPlanItem 表
        migrations.DeleteModel(
            name="LearningPlanItem",
        ),

        # 2. 给 LearningPlan 加新字段（item 提升上来）
        migrations.AddField(
            model_name="learningplan",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("study", "阅读学习"),
                    ("practice", "刷题巩固"),
                    ("chat", "对话学习"),
                    ("video", "视频学习"),
                ],
                default="study",
                max_length=20,
                verbose_name="推荐动作",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="actual_completion_time",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="实际完成时间",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="completed",
            field=models.BooleanField(default=False, verbose_name="是否完成"),
        ),
        # 节点难度 1-5（替换旧 difficulty 字段名，但 type 不同）
        migrations.AddField(
            model_name="learningplan",
            name="difficulty",
            field=models.PositiveSmallIntegerField(
                default=1, db_index=True, verbose_name="节点难度",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="expected_minutes",
            field=models.PositiveIntegerField(
                default=30, verbose_name="预计耗时（分钟）",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="node_id",
            field=models.CharField(
                db_index=True, default="", max_length=32, verbose_name="知识点 ID",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="node_name",
            field=models.CharField(
                db_index=True, default="", max_length=100, verbose_name="知识点名称",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="node_type",
            field=models.CharField(
                blank=True, default="", max_length=32, verbose_name="知识点类型",
            ),
        ),
        migrations.AddField(
            model_name="learningplan",
            name="order",
            field=models.PositiveIntegerField(
                db_index=True, default=0, verbose_name="计划项顺序",
            ),
        ),

        # 3. state 加 db_index
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
                db_index=True,
                default="pending",
                max_length=20,
                verbose_name="计划状态",
            ),
        ),

        # 4. expected_completion_time 加 db_index
        migrations.AlterField(
            model_name="learningplan",
            name="expected_completion_time",
            field=models.DateTimeField(
                blank=True, db_index=True, null=True, verbose_name="预计完成时间",
            ),
        ),

        # 5. 添加复合索引
        migrations.AddIndex(
            model_name="learningplan",
            index=models.Index(
                fields=["subject", "state"],
                name="plan_learni_subject__4e1a4a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="learningplan",
            index=models.Index(
                fields=["subject", "node_name"],
                name="plan_learni_subject__a9b2c3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="learningplan",
            index=models.Index(
                fields=["subject", "target_agent"],
                name="plan_learni_subject__d8e7f6_idx",
            ),
        ),
    ]
