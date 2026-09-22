#!/usr/bin/env python3
"""V1.1-RC2 fail-closed gate runner.

This runner does not pretend to direct a film. It verifies that upstream AI
modules produced the required, machine-readable evidence before a final prompt
may be compiled or released.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_FILES = {
    "input": "01_user_input.json",
    "precheck": "02_director_precheck.json",
    "expansion": "03_action_expansion.json",
    "ledger": "04_world_state_ledger.json",
    "timeline": "05_interaction_timeline.json",
    "dispatch": "06_dispatch_plan.json",
    "failures": "07_failure_matches.json",
    "progression": "08_tactical_emotional_arc.json",
    "review": "09_adversarial_review.json",
    "gates": "10_gate_state.json",
    "draft": "11_prompt_draft.md",
}

PASS_STATUSES = {"PASS", "NOT_REQUIRED"}
RULES_PATH = Path(__file__).resolve().parents[1] / "core" / "V1.1-RC2" / "04_失败规则" / "failure_rules.json"


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"缺少文件：{path.name}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON格式错误：{path.name}（{exc.msg}）")
    if not isinstance(data, dict):
        raise ValueError(f"文件顶层必须是对象：{path.name}")
    return data


def nonempty(value) -> bool:
    return value not in (None, "", [], {})


def require(data: dict, keys: list[str], label: str, errors: list[str]) -> None:
    for key in keys:
        if key not in data or data.get(key) is None:
            errors.append(f"{label}缺少必填字段：{key}")


def validate_input(data: dict, errors: list[str]) -> None:
    require(data, ["project_id", "source_text", "target_model", "clip_seconds", "is_action_scene",
                   "is_key_action_scene", "action_detail_level", "assets"], "用户输入", errors)
    for key in ("project_id", "source_text", "target_model"):
        if not nonempty(data.get(key)):
            errors.append(f"用户输入字段不得为空：{key}")
    seconds = data.get("clip_seconds")
    if not isinstance(seconds, (int, float)) or seconds <= 0:
        errors.append("clip_seconds必须是大于0的数字")
    assets = data.get("assets", [])
    if not isinstance(assets, list) or not assets:
        errors.append("assets必须是非空列表")
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"assets[{index}]必须是对象")
            continue
        require(asset, ["asset_id", "canonical_name", "category", "status"], f"assets[{index}]", errors)


def validate_precheck(data: dict, errors: list[str]) -> None:
    require(data, ["status", "plan_session_id", "story_trigger", "protagonist_goal", "opponent_goal", "protagonist_reaction", "blocking_issues"], "导演预检", errors)
    if not nonempty(data.get("plan_session_id")):
        errors.append("导演预检缺少方案会话标识")
    for key in ("story_trigger", "protagonist_goal", "opponent_goal", "protagonist_reaction"):
        if not nonempty(data.get(key)):
            errors.append(f"导演预检字段不得为空：{key}")
    if data.get("status") != "PASS":
        errors.append("导演预检未通过")
    if data.get("blocking_issues"):
        errors.append("导演预检仍有阻塞项")


def validate_expansion(data: dict, user_input: dict, errors: list[str]) -> None:
    require(data, ["required", "status", "source_action_density", "reason", "original_beats",
                   "proposed_beats", "preserved_facts", "user_decision"], "动作扩写确认", errors)
    required = data.get("required")
    status = data.get("status")
    if not isinstance(required, bool):
        errors.append("动作扩写确认required必须是布尔值")
        return
    if status not in {"NOT_REQUIRED", "PENDING_USER", "APPROVED", "REJECTED"}:
        errors.append("动作扩写确认status无效")
    if required and status != "APPROVED":
        errors.append(f"动作扩写尚未获得用户确认：{status}")
    if not required and status != "NOT_REQUIRED":
        errors.append("不需要扩写时status必须为NOT_REQUIRED")
    if required and len(data.get("proposed_beats", [])) < 3:
        errors.append("动作扩写至少需要3个有功能的动作Beat")
    if required and not nonempty(data.get("user_decision")):
        errors.append("动作扩写缺少用户确认记录")
    if user_input.get("is_action_scene") and user_input.get("action_detail_level") == "thin" and not required:
        errors.append("动作信息过薄却未触发扩写确认门")
    if user_input.get("is_key_action_scene") and len(data.get("original_beats", [])) < 3 and not required:
        errors.append("关键动作场原始Beat不足却未触发扩写确认门")


def validate_ledger(data: dict, errors: list[str]) -> None:
    require(data, ["status", "shots"], "世界状态账本", errors)
    if data.get("status") != "PASS":
        errors.append("世界状态账本未通过")
    shots = data.get("shots", [])
    if not isinstance(shots, list) or not shots:
        errors.append("世界状态账本至少需要一个镜头状态")
        return
    required = ["shot_id", "start_state", "end_state"]
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots[{index}]必须是对象")
            continue
        require(shot, required, f"shots[{index}]", errors)
        if index:
            previous = shots[index - 1].get("end_state")
            current = shot.get("start_state")
            if previous != current:
                errors.append(f"状态断裂：{shots[index-1].get('shot_id')}结束状态与{shot.get('shot_id')}开始状态不一致")


def validate_timeline(data: dict, errors: list[str]) -> None:
    require(data, ["status", "time_unit", "exchanges"], "攻防交互时间线", errors)
    if data.get("status") != "PASS":
        errors.append("攻防交互时间线未通过")
    if data.get("time_unit") != "seconds":
        errors.append("攻防交互时间线必须使用seconds")
    exchanges = data.get("exchanges", [])
    if not isinstance(exchanges, list) or not exchanges:
        errors.append("攻防交互时间线至少需要一次攻防交换")
        return
    for index, item in enumerate(exchanges):
        label = f"exchanges[{index}]"
        require(item, ["exchange_id", "attacker", "defender", "attack_start", "defender_perception",
                       "defense_start", "contact", "force_transfer", "defender_reaction"], label, errors)
        contact = item.get("contact", {})
        require(contact, ["attack_time", "defense_time", "attack_location", "defense_location",
                          "physical_contact_visible"], f"{label}.contact", errors)
        try:
            attack_start = float(item["attack_start"])
            perception = float(item["defender_perception"])
            defense_start = float(item["defense_start"])
            attack_time = float(contact["attack_time"])
            defense_time = float(contact["defense_time"])
            force_transfer = float(item["force_transfer"])
            reaction = float(item["defender_reaction"])
            environment = float(item.get("environment_reaction", reaction))
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}时间字段必须是数字")
            continue
        if not attack_start <= perception <= defense_start < attack_time:
            errors.append(f"{label}攻防不同步：必须先攻击起势，再察觉并开始防御，最后才接触")
        if abs(attack_time - defense_time) > 0.02:
            errors.append(f"{label}双方接触时间不一致")
        if contact.get("attack_location") != contact.get("defense_location"):
            errors.append(f"{label}双方接触位置不一致")
        if contact.get("physical_contact_visible") is not True:
            errors.append(f"{label}未确认可见实体接触")
        if force_transfer < attack_time or reaction < force_transfer:
            errors.append(f"{label}受力顺序错误：力量传递和身体反馈不得早于实体接触")
        if environment < attack_time:
            errors.append(f"{label}环境反馈不得早于实体接触")


def validate_dispatch(data: dict, user_input: dict, errors: list[str]) -> None:
    require(data, ["status", "risk_level", "axis", "actors", "routes", "distance_checks"], "调度数据", errors)
    if data.get("status") != "PASS":
        errors.append("调度数据未通过")
    risk = data.get("risk_level")
    if risk not in {"low", "medium", "high"}:
        errors.append("risk_level只能是low/medium/high")
    if risk == "high" and not data.get("topology_complete"):
        errors.append("高风险动作缺少完整结构化调度图数据")
    if not data.get("routes"):
        errors.append("动作路线为空")
    if "F-TACTIC-001" in expected_failure_ids(user_input) and len(data.get("route_dimensions", [])) < 2:
        errors.append("连续战斗路线过直：至少需要两种空间维度")
    if user_input.get("contains_large_scale_action") and not data.get("release_distance_verified"):
        errors.append("大型法器/范围动作未验证释放距离")
    if user_input.get("contains_large_scale_action"):
        if risk != "high":
            errors.append("大型法器/范围动作必须标记为high风险")
        if len(data.get("route_dimensions", [])) < 2:
            errors.append("高风险动作路线缺少至少两种空间维度")
        if not data.get("scale_references"):
            errors.append("大型法器缺少人物或环境尺度参照")
        if len(data.get("release_steps", [])) < 3:
            errors.append("大型法器缺少完整释放过程")


def expected_failure_ids(user_input: dict) -> set[str]:
    corpus = " ".join([
        str(user_input.get("source_text", "")),
        str(user_input.get("preferences", "")),
        " ".join(map(str, user_input.get("must_keep", []))),
    ])
    try:
        rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    expected = set()
    for rule in rules:
        if any(trigger in corpus for trigger in rule.get("triggers", [])):
            expected.add(rule["failure_id"])
    if user_input.get("contains_large_scale_action"):
        expected.add("F-SCALE-001")
    for asset in user_input.get("assets", []):
        if asset.get("status") == "confirmed":
            expected.add("F-TERM-001")
    return expected


def validate_failure_matches(data: dict, user_input: dict, errors: list[str]) -> None:
    require(data, ["status", "matches", "checks_applied"], "失败案例匹配", errors)
    if data.get("status") != "PASS":
        errors.append("失败案例匹配未通过")
    unresolved = [m for m in data.get("matches", []) if m.get("triggered") and not m.get("resolved")]
    if unresolved:
        errors.append("存在未解决的历史失败风险：" + ", ".join(str(m.get("failure_id")) for m in unresolved))
    supplied = {m.get("failure_id") for m in data.get("matches", []) if m.get("triggered")}
    missing = sorted(expected_failure_ids(user_input) - supplied)
    if missing:
        errors.append("历史失败规则未自动挂载：" + ", ".join(missing))


def validate_progression(data: dict, user_input: dict, errors: list[str]) -> None:
    require(data, ["status", "pattern", "stages", "progression_verified"], "战术情绪递进", errors)
    if data.get("status") != "PASS":
        errors.append("战术情绪递进未通过")
    if data.get("progression_verified") is not True:
        errors.append("战术情绪变化尚未验证")
    stages = data.get("stages", [])
    minimum = 2 if user_input.get("is_action_scene") else 1
    if not isinstance(stages, list) or len(stages) < minimum:
        errors.append(f"战术情绪递进至少需要{minimum}个阶段")
        return
    previous_end = None
    signatures = set()
    for index, stage in enumerate(stages):
        require(stage, ["stage_id", "time_start", "time_end", "tactic", "emotion", "intensity",
                        "change_cause", "dramatic_function"], f"stages[{index}]", errors)
        if not nonempty(stage.get("change_cause")) or not nonempty(stage.get("dramatic_function")):
            errors.append(f"stages[{index}]缺少变化原因或戏剧功能")
        try:
            start, end = float(stage["time_start"]), float(stage["time_end"])
            intensity = int(stage["intensity"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"stages[{index}]时间与强度必须为数字")
            continue
        if start >= end or not 1 <= intensity <= 5:
            errors.append(f"stages[{index}]时间范围或强度无效")
        if previous_end is not None and abs(start - previous_end) > 0.02:
            errors.append(f"战术情绪阶段时间不连续：stages[{index}]")
        previous_end = end
        signatures.add((str(stage.get("tactic")), str(stage.get("emotion")), intensity))
    if user_input.get("is_action_scene") and len(signatures) < 2:
        errors.append("动作场战术、情绪与强度始终不变")


def validate_review(data: dict, precheck: dict, errors: list[str]) -> None:
    require(data, ["status", "reviewer_role", "review_session_id", "findings", "hard_failures", "checks"], "独立反方审查", errors)
    if data.get("status") != "PASS":
        errors.append("独立反方审查未通过")
    if data.get("hard_failures"):
        errors.append("独立反方审查存在硬失败")
    if data.get("reviewer_role") != "independent_adversarial_reviewer":
        errors.append("反方审查角色标识无效")
    if not nonempty(data.get("review_session_id")):
        errors.append("反方审查缺少独立会话标识")
    if data.get("review_session_id") == precheck.get("plan_session_id"):
        errors.append("反方审查与方案生成使用了同一会话标识")
    checks = data.get("checks", {})
    for key in ("expansion_compliance", "attack_defense_synchronized", "contact_visible",
                "force_order_valid", "tactical_emotional_progression", "state_continuity",
                "asset_terms_locked"):
        if checks.get(key) is not True:
            errors.append(f"反方审查未通过检查：{key}")


def validate_gates(data: dict, errors: list[str]) -> None:
    require(data, ["pipeline_version", "stages"], "门禁状态", errors)
    if data.get("pipeline_version") != "1.1.0-rc.2":
        errors.append("门禁状态版本不匹配")
    stages = data.get("stages", {})
    for stage in ("S1_DIRECTOR", "S2_EXPANSION", "S3_ASSET", "S4_SPACE", "S5_INTERACTION",
                  "S6_CAMERA", "S7_REVIEW", "S8_GENERATION"):
        status = stages.get(stage, {}).get("status") if isinstance(stages.get(stage), dict) else None
        if status not in PASS_STATUSES:
            errors.append(f"阶段门未通过：{stage}={status or 'MISSING'}")


def validate_terms(user_input: dict, draft: str, errors: list[str]) -> None:
    for asset in user_input.get("assets", []):
        canonical = asset.get("canonical_name")
        if asset.get("status") == "confirmed" and canonical and canonical not in draft:
            errors.append(f"成品Prompt遗漏锁定资产名：{canonical}")
        for alias in asset.get("forbidden_output_aliases", []):
            if alias and re.search(re.escape(alias), draft):
                errors.append(f"成品Prompt出现禁用替代名：{alias}")


def validate(project_dir: Path) -> list[str]:
    errors: list[str] = []
    data = {}
    for key, filename in REQUIRED_FILES.items():
        path = project_dir / filename
        if not path.exists():
            errors.append(f"缺少文件：{filename}")
            continue
        if key != "draft":
            try:
                data[key] = read_json(path)
            except ValueError as exc:
                errors.append(str(exc))
        else:
            data[key] = path.read_text(encoding="utf-8").strip()
            if not data[key]:
                errors.append("11_prompt_draft.md为空")
    if errors:
        return errors
    validate_input(data["input"], errors)
    validate_precheck(data["precheck"], errors)
    validate_expansion(data["expansion"], data["input"], errors)
    validate_ledger(data["ledger"], errors)
    validate_timeline(data["timeline"], errors)
    validate_dispatch(data["dispatch"], data["input"], errors)
    validate_failure_matches(data["failures"], data["input"], errors)
    validate_progression(data["progression"], data["input"], errors)
    validate_review(data["review"], data["precheck"], errors)
    validate_gates(data["gates"], errors)
    validate_terms(data["input"], data["draft"], errors)
    return errors


def init_project(project_dir: Path, force: bool = False) -> None:
    template_dir = Path(__file__).resolve().parents[1] / "core" / "V1.1-RC2" / "03_数据模板"
    project_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        "01_user_input.template.json": "01_user_input.json",
        "02_director_precheck.template.json": "02_director_precheck.json",
        "03_action_expansion.template.json": "03_action_expansion.json",
        "04_world_state_ledger.template.json": "04_world_state_ledger.json",
        "05_interaction_timeline.template.json": "05_interaction_timeline.json",
        "06_dispatch_plan.template.json": "06_dispatch_plan.json",
        "07_failure_matches.template.json": "07_failure_matches.json",
        "08_tactical_emotional_arc.template.json": "08_tactical_emotional_arc.json",
        "09_adversarial_review.template.json": "09_adversarial_review.json",
        "10_gate_state.template.json": "10_gate_state.json",
        "11_prompt_draft.template.md": "11_prompt_draft.md",
    }
    for source, target in mapping.items():
        destination = project_dir / target
        if destination.exists() and not force:
            continue
        destination.write_text((template_dir / source).read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="V1.1-RC2生成门禁")
    sub = parser.add_subparsers(dest="command", required=True)
    init_cmd = sub.add_parser("init", help="创建项目任务包")
    init_cmd.add_argument("project_dir", type=Path)
    init_cmd.add_argument("--force", action="store_true")
    validate_cmd = sub.add_parser("validate", help="检查能否进入生成")
    validate_cmd.add_argument("project_dir", type=Path)
    compile_cmd = sub.add_parser("compile", help="通过门禁后输出最终Prompt")
    compile_cmd.add_argument("project_dir", type=Path)
    args = parser.parse_args()

    if args.command == "init":
        init_project(args.project_dir, args.force)
        print(f"任务包已创建：{args.project_dir}")
        return 0

    errors = validate(args.project_dir)
    if errors:
        print("BLOCKED：未通过V1.1-RC2生成门禁", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print("PASS：允许进入Prompt编译/生成")
        return 0
    final_path = args.project_dir / "12_final_prompt.md"
    draft = (args.project_dir / REQUIRED_FILES["draft"]).read_text(encoding="utf-8")
    final_path.write_text(draft, encoding="utf-8")
    print(f"PASS：已输出 {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
