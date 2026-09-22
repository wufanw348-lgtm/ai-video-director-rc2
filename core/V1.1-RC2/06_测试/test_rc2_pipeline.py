import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from rc2_pipeline import init_project, validate


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        init_project(self.project)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        (self.project / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def make_valid(self):
        self.write("01_user_input.json", {
            "project_id": "REG-WZ-03", "source_text": "甲追击乙。", "target_model": "Seedance 2.5",
            "clip_seconds": 8, "contains_large_scale_action": False, "is_action_scene": True,
            "is_key_action_scene": True, "action_detail_level": "thin",
            "assets": [{"asset_id": "A1", "canonical_name": "法宝甲", "category": "prop", "status": "confirmed", "forbidden_output_aliases": ["神兵"]}]
        })
        self.write("02_director_precheck.json", {"status": "PASS", "plan_session_id": "PLAN-1", "story_trigger": "争夺", "protagonist_goal": "阻止", "opponent_goal": "逃脱", "protagonist_reaction": "追击", "blocking_issues": []})
        self.write("03_action_expansion.json", {"required": True, "status": "APPROVED", "source_action_density": "thin", "reason": "关键动作过薄", "original_beats": ["追击"], "proposed_beats": ["逼近", "变向拦截", "碰撞反制"], "preserved_facts": ["甲追乙"], "user_decision": "采用推荐扩写"})
        state = {"甲": {"x": 0}, "乙": {"x": 5}}
        self.write("04_world_state_ledger.json", {"status": "PASS", "shots": [{"shot_id": "SH01", "start_state": state, "end_state": state}]})
        self.write("05_interaction_timeline.json", {"status": "PASS", "time_unit": "seconds", "exchanges": [{"exchange_id": "EX1", "attacker": "甲", "defender": "乙", "attack_start": 0.4, "defender_perception": 0.7, "defense_start": 0.9, "contact": {"attack_time": 1.4, "defense_time": 1.4, "attack_location": "乙左肩前", "defense_location": "乙左肩前", "physical_contact_visible": True}, "force_transfer": 1.4, "defender_reaction": 1.5, "environment_reaction": 1.6}]})
        self.write("06_dispatch_plan.json", {"status": "PASS", "risk_level": "medium", "axis": "甲乙轴线北侧", "actors": ["甲", "乙"], "routes": ["甲向前", "乙横移"], "route_dimensions": ["纵深", "横向"], "distance_checks": ["5米"], "topology_complete": True, "release_distance_verified": False})
        self.write("07_failure_matches.json", {"status": "PASS", "matches": [{"failure_id": "F-TERM-001", "triggered": True, "resolved": True}], "checks_applied": ["F-TERM-001"]})
        self.write("08_tactical_emotional_arc.json", {"status": "PASS", "pattern": "追击反制", "progression_verified": True, "stages": [{"stage_id": "AR1", "time_start": 0.0, "time_end": 1.4, "tactic": "逼近试探", "emotion": "警惕", "intensity": 2, "change_cause": "甲缩短距离", "dramatic_function": "建立威胁"}, {"stage_id": "AR2", "time_start": 1.4, "time_end": 3.0, "tactic": "碰撞反制", "emotion": "决断", "intensity": 4, "change_cause": "乙完成拦截", "dramatic_function": "形成转折"}]})
        self.write("09_adversarial_review.json", {"status": "PASS", "reviewer_role": "independent_adversarial_reviewer", "review_session_id": "REVIEW-2", "findings": [], "hard_failures": [], "checks": {"expansion_compliance": True, "attack_defense_synchronized": True, "contact_visible": True, "force_order_valid": True, "tactical_emotional_progression": True, "state_continuity": True, "asset_terms_locked": True}})
        self.write("10_gate_state.json", {"pipeline_version": "1.1.0-rc.2", "stages": {key: {"status": "PASS"} for key in ["S1_DIRECTOR", "S2_EXPANSION", "S3_ASSET", "S4_SPACE", "S5_INTERACTION", "S6_CAMERA", "S7_REVIEW", "S8_GENERATION"]}})
        (self.project / "11_prompt_draft.md").write_text("甲使用法宝甲完成一次攻击。", encoding="utf-8")

    def test_empty_template_is_blocked(self):
        self.assertTrue(validate(self.project))

    def test_valid_package_passes(self):
        self.make_valid()
        self.assertEqual(validate(self.project), [])

    def test_compile_only_after_pass(self):
        self.make_valid()
        self.assertEqual(validate(self.project), [])
        self.assertFalse((self.project / "12_final_prompt.md").exists())

    def test_continuity_break_is_blocked(self):
        self.make_valid()
        self.write("04_world_state_ledger.json", {"status": "PASS", "shots": [
            {"shot_id": "SH01", "start_state": {"甲": {"x": 0}}, "end_state": {"甲": {"x": 2}}},
            {"shot_id": "SH02", "start_state": {"甲": {"x": 9}}, "end_state": {"甲": {"x": 10}}}
        ]})
        self.assertTrue(any("状态断裂" in e for e in validate(self.project)))

    def test_forbidden_alias_is_blocked(self):
        self.make_valid()
        (self.project / "11_prompt_draft.md").write_text("甲使用法宝甲，又称神兵。", encoding="utf-8")
        self.assertTrue(any("禁用替代名" in e for e in validate(self.project)))

    def test_large_action_requires_distance(self):
        self.make_valid()
        data = json.loads((self.project / "01_user_input.json").read_text(encoding="utf-8"))
        data["contains_large_scale_action"] = True
        self.write("01_user_input.json", data)
        self.assertTrue(any("释放距离" in e for e in validate(self.project)))

    def test_missing_automatic_failure_match_is_blocked(self):
        self.make_valid()
        data = json.loads((self.project / "01_user_input.json").read_text(encoding="utf-8"))
        data["source_text"] = "两人开始连续攻击和碰撞。"
        self.write("01_user_input.json", data)
        self.assertTrue(any("历史失败规则未自动挂载" in e for e in validate(self.project)))

    def test_resolved_label_cannot_hide_straight_route(self):
        self.make_valid()
        data = json.loads((self.project / "01_user_input.json").read_text(encoding="utf-8"))
        data["source_text"] = "两人开始连续攻击。"
        self.write("01_user_input.json", data)
        matches = json.loads((self.project / "07_failure_matches.json").read_text(encoding="utf-8"))
        matches["matches"].append({"failure_id": "F-TACTIC-001", "triggered": True, "resolved": True})
        self.write("07_failure_matches.json", matches)
        dispatch = json.loads((self.project / "06_dispatch_plan.json").read_text(encoding="utf-8"))
        dispatch["route_dimensions"] = ["纵深"]
        self.write("06_dispatch_plan.json", dispatch)
        self.assertTrue(any("路线过直" in e for e in validate(self.project)))

    def test_expansion_pending_blocks(self):
        self.make_valid()
        data = json.loads((self.project / "03_action_expansion.json").read_text(encoding="utf-8"))
        data["status"] = "PENDING_USER"
        data["user_decision"] = ""
        self.write("03_action_expansion.json", data)
        self.assertTrue(any("扩写尚未获得用户确认" in e for e in validate(self.project)))

    def test_defense_after_contact_blocks(self):
        self.make_valid()
        data = json.loads((self.project / "05_interaction_timeline.json").read_text(encoding="utf-8"))
        data["exchanges"][0]["defense_start"] = 1.6
        self.write("05_interaction_timeline.json", data)
        self.assertTrue(any("攻防不同步" in e for e in validate(self.project)))

    def test_contact_time_or_location_mismatch_blocks(self):
        self.make_valid()
        data = json.loads((self.project / "05_interaction_timeline.json").read_text(encoding="utf-8"))
        data["exchanges"][0]["contact"]["defense_time"] = 1.7
        data["exchanges"][0]["contact"]["defense_location"] = "乙右肩"
        self.write("05_interaction_timeline.json", data)
        errors = validate(self.project)
        self.assertTrue(any("接触时间不一致" in e for e in errors))
        self.assertTrue(any("接触位置不一致" in e for e in errors))

    def test_flat_tactical_emotional_arc_blocks(self):
        self.make_valid()
        data = json.loads((self.project / "08_tactical_emotional_arc.json").read_text(encoding="utf-8"))
        data["stages"][1].update({"tactic": "逼近试探", "emotion": "警惕", "intensity": 2})
        self.write("08_tactical_emotional_arc.json", data)
        self.assertTrue(any("始终不变" in e for e in validate(self.project)))

    def test_same_planner_and_reviewer_session_blocks(self):
        self.make_valid()
        data = json.loads((self.project / "09_adversarial_review.json").read_text(encoding="utf-8"))
        data["review_session_id"] = "PLAN-1"
        self.write("09_adversarial_review.json", data)
        self.assertTrue(any("同一会话标识" in e for e in validate(self.project)))


if __name__ == "__main__":
    unittest.main()
