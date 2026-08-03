from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase

from llm.agents.knowledge_assessor import AssessmentResult
from llm.tasks import _maybe_update_knowledge_from_practice
from quiz.models import QuizGenerationRecord
from .models import Conversation, Subject, User
from .models import KnowledgeNode, UserProfile


class ConversationCreateExtraPromptTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.user)
        self.subject = Subject.objects.create(user=self.user, name="data_structure")

    def test_create_conversation_accepts_extra_prompt(self):
        extra_prompt = "你正在执行一个学习计划，请围绕链表薄弱点继续出题。"
        with patch("users.serializers.cache.get", return_value=None):
            response = self.client.post(
                "/api/conversations/",
                {
                    "subject_id": self.subject.id,
                    "title": "链表专项练习",
                    "agent": Conversation.AGENT_PRACTICE,
                    "extra_prompt": extra_prompt,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["extra_prompt"], extra_prompt)

        conversation = Conversation.objects.get(id=response.data["id"])
        self.assertEqual(conversation.extra_prompt, extra_prompt)

    def test_create_conversation_accepts_agent_payload_and_handoff(self):
        handoff = {
            "from_agent": "plan",
            "next_agent": Conversation.AGENT_PRACTICE,
            "payload": {
                "mode": "plan_driven",
                "plan_id": 12,
                "difficulty": "medium",
                "focus_nodes": ["链表", "二叉树"],
            },
            "extra_prompt": "优先考察基础概念和常见操作",
        }
        with patch("users.serializers.cache.get", return_value=None):
            response = self.client.post(
                "/api/conversations/",
                {
                    "subject_id": self.subject.id,
                    "title": "计划驱动练习",
                    "agent": Conversation.AGENT_PRACTICE,
                    "handoff": handoff,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["extra_prompt"], handoff["extra_prompt"])
        self.assertEqual(response.data["agent_payload"], handoff["payload"])
        self.assertEqual(response.data["handoff"], handoff)

        conversation = Conversation.objects.get(id=response.data["id"])
        self.assertEqual(conversation.agent_payload, handoff["payload"])
        self.assertEqual(conversation.handoff, handoff)

    def test_create_conversation_rejects_invalid_plan_payload(self):
        with patch("users.serializers.cache.get", return_value=None):
            response = self.client.post(
                "/api/conversations/",
                {
                    "subject_id": self.subject.id,
                    "title": "计划编辑",
                    "agent": Conversation.AGENT_PLAN,
                    "agent_payload": {
                        "mode": "edit",
                        "selected_plan_ids": "1,2,3",
                    },
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("selected_plan_ids", response.data["error"])


class PracticeKnowledgeUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="practice_user",
            email="practice@example.com",
            password="password123",
        )
        self.subject = Subject.objects.create(user=self.user, name="data_structure")
        self.node = KnowledgeNode.objects.create(
            subject=self.subject,
            node_id="3",
            name="链表",
            mastery=40,
        )
        self.quiz_record = QuizGenerationRecord.objects.create(
            user=self.user,
            subject=self.subject,
            task_id="quiz-task-1",
            state=QuizGenerationRecord.STATE_COMPLETE,
            questions=[
                {
                    "knowledge_node_id": "3",
                    "knowledge_node_name": "链表",
                    "question_text": "链表适合频繁在哪种位置插入？",
                    "correct_answer": "头部或已知节点后插入",
                }
            ],
        )

    def test_with_answer_updates_knowledge_node(self):
        analysis_result = {
            "analysis": "用户理解了链表插入的核心特征。",
            "result": {
                "verdict": "correct",
                "is_correct": True,
                "user_answer": "头插和在已知节点后插入都很高效",
                "correct_answer": "头部或已知节点后插入",
                "summary": "回答正确，体现出对链表插入场景的理解。",
            },
        }

        fake_result = AssessmentResult(
            new_score=52,
            prev_score=40,
            delta_norm=0.5,
            actual_delta=12,
            max_delta_used=25,
            rationale="mocked",
            raw_outputs=["0.5"],
        )

        with patch("llm.tools.knowledge_tools.get_assessor") as mocked_get_assessor:
            mocked_get_assessor.return_value.assess.return_value = fake_result
            update_info = _maybe_update_knowledge_from_practice(
                quiz_record=self.quiz_record,
                question_index=0,
                analysis_result=analysis_result,
                user_answer="头插和在已知节点后插入都很高效",
            )

        self.assertIsNotNone(update_info)
        self.node.refresh_from_db()
        self.assertEqual(self.node.mastery, 52)
        self.assertEqual(len(self.node.evidence_log), 1)
        self.assertEqual(self.node.evidence_log[0]["new"], 52)

    def test_wrong_answer_updates_common_mistakes(self):
        analysis_result = {
            "analysis": "用户混淆了链表插入位置和数组插入特点。",
            "result": {
                "verdict": "wrong",
                "is_correct": False,
                "user_answer": "尾部插入总是最快",
                "correct_answer": "头部或已知节点后插入",
                "summary": "回答错误，说明对链表插入场景理解不足。",
            },
        }

        fake_result = AssessmentResult(
            new_score=32,
            prev_score=40,
            delta_norm=-0.3,
            actual_delta=-8,
            max_delta_used=25,
            rationale="mocked",
            raw_outputs=["-0.3"],
        )

        with patch("llm.tools.knowledge_tools.get_assessor") as mocked_get_assessor:
            mocked_get_assessor.return_value.assess.return_value = fake_result
            update_info = _maybe_update_knowledge_from_practice(
                quiz_record=self.quiz_record,
                question_index=0,
                analysis_result=analysis_result,
                user_answer="尾部插入总是最快",
            )

        self.assertIsNotNone(update_info)
        profile = UserProfile.objects.get(subject=self.subject)
        self.assertIn("链表", profile.common_mistakes)
        self.assertIsNotNone(update_info["profile_update"])
        self.assertEqual(update_info["profile_update"]["added_node"], "链表")

    def test_correct_answer_removes_common_mistake_after_recovery(self):
        UserProfile.objects.create(subject=self.subject, common_mistakes=["链表"])
        self.node.evidence_log = [
            {
                "metadata": {
                    "source": "practice_with_answer",
                    "is_correct": True,
                }
            }
        ]
        self.node.mastery = 48
        self.node.save(update_fields=["mastery", "evidence_log", "updated_at"])

        analysis_result = {
            "analysis": "用户这次对链表插入已经理解到位。",
            "result": {
                "verdict": "correct",
                "is_correct": True,
                "user_answer": "头部或已知节点后插入效率更高",
                "correct_answer": "头部或已知节点后插入",
                "summary": "连续答对，说明该知识点掌握度明显提升。",
            },
        }

        fake_result = AssessmentResult(
            new_score=65,
            prev_score=48,
            delta_norm=0.7,
            actual_delta=17,
            max_delta_used=25,
            rationale="mocked",
            raw_outputs=["0.7"],
        )

        with patch("llm.tools.knowledge_tools.get_assessor") as mocked_get_assessor:
            mocked_get_assessor.return_value.assess.return_value = fake_result
            update_info = _maybe_update_knowledge_from_practice(
                quiz_record=self.quiz_record,
                question_index=0,
                analysis_result=analysis_result,
                user_answer="头部或已知节点后插入效率更高",
            )

        self.assertIsNotNone(update_info)
        profile = UserProfile.objects.get(subject=self.subject)
        self.assertNotIn("链表", profile.common_mistakes)
        self.assertIsNotNone(update_info["profile_update"])
        self.assertEqual(update_info["profile_update"]["removed_node"], "链表")
