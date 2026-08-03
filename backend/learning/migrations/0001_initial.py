from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("users", "0015_alter_conversation_agent"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudySession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("activity_type", models.CharField(
                    choices=[("chat", "对话"), ("reading", "看书"), ("video", "视频"), ("quiz", "刷题"), ("exam", "评测")],
                    max_length=20, verbose_name="活动类型",
                )),
                ("date", models.DateField(verbose_name="日期")),
                ("duration_minutes", models.PositiveIntegerField(default=0, verbose_name="学习时长(分钟)")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="study_sessions", to="users.user")),
                ("subject", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="study_sessions", to="users.subject")),
            ],
            options={
                "verbose_name": "学习时长记录",
                "verbose_name_plural": "学习时长记录",
                "ordering": ["-date", "activity_type"],
                "unique_together": {("user", "subject", "date", "activity_type")},
            },
        ),
        migrations.AddIndex(
            model_name="studysession",
            index=models.Index(fields=["user", "date"], name="learning_s_user_id_date_idx"),
        ),
        migrations.AddIndex(
            model_name="studysession",
            index=models.Index(fields=["subject", "date"], name="learning_s_subject_id_date_idx"),
        ),
    ]
