from .models import UserProfile


def get_profile_snapshot(subject) -> dict:
    profile = UserProfile.objects.filter(subject=subject).first()
    if profile is None:
        return {
            "learning_goal": {"goal": "", "priority": 1, "target_date": "", "difficulty_level": "beginner"},
            "knowledge_base": {"level": 0, "strong_areas": [], "weak_areas": [], "recommended_courses": []},
            "cognitive_style": {"style_type": "analytical", "description": "", "score": 0},
            "available_time": 0,
            "interest_direction": [],
            "common_mistakes": [],
            "course": "",
        }
    return {
        "learning_goal": {"goal": "", "priority": profile.learning_goal_score or 1, "target_date": "", "difficulty_level": "beginner"},
        "knowledge_base": {
            "level": profile.knowledge_base or 0,
            "strong_areas": [],
            "weak_areas": list(profile.common_mistakes or []),
            "recommended_courses": [],
        },
        "cognitive_style": {"style_type": "analytical", "description": "", "score": profile.cognitive_style or 0},
        "available_time": profile.available_time or 0,
        "interest_direction": list(profile.interest_direction or []),
        "common_mistakes": list(profile.common_mistakes or []),
        "course": profile.course or "",
    }


def save_profile_snapshot(subject, profile: dict) -> None:
    if not profile:
        return

    kb = profile.get("knowledge_base") or {}
    cs = profile.get("cognitive_style") or {}
    lg = profile.get("learning_goal") or {}
    profile_obj, _ = UserProfile.objects.get_or_create(subject=subject)

    profile_obj.knowledge_base = kb.get("level") or 0
    profile_obj.cognitive_style = cs.get("score") or 0
    profile_obj.learning_goal_score = lg.get("priority") or 0
    profile_obj.learning_goal = lg.get("goal") or ""
    profile_obj.available_time = profile.get("available_time") or 0
    profile_obj.course = profile.get("course") or ""
    if isinstance(profile.get("common_mistakes"), list):
        profile_obj.common_mistakes = profile.get("common_mistakes")
    if isinstance(profile.get("interest_direction"), list):
        profile_obj.interest_direction = profile.get("interest_direction")
    profile_obj.save()


def add_common_mistake(subject, node_name: str) -> list[str]:
    """将知识点加入用户画像的易错点列表，重复值会自动去重。"""
    normalized_name = str(node_name or "").strip()
    if not normalized_name:
        return []

    profile_obj, _ = UserProfile.objects.get_or_create(subject=subject)
    mistakes = [str(item).strip() for item in (profile_obj.common_mistakes or []) if str(item).strip()]
    if normalized_name not in mistakes:
        mistakes.append(normalized_name)
        profile_obj.common_mistakes = mistakes
        profile_obj.save(update_fields=["common_mistakes", "updated_at"])
    return mistakes


def remove_common_mistake(subject, node_name: str) -> list[str]:
    """将知识点从用户画像的易错点列表中移除。"""
    normalized_name = str(node_name or "").strip()
    profile_obj, _ = UserProfile.objects.get_or_create(subject=subject)
    mistakes = [str(item).strip() for item in (profile_obj.common_mistakes or []) if str(item).strip()]
    updated = [item for item in mistakes if item != normalized_name]
    if updated != mistakes:
        profile_obj.common_mistakes = updated
        profile_obj.save(update_fields=["common_mistakes", "updated_at"])
    return updated
