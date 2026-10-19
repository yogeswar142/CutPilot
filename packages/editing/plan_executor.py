"""
CutPilot Plan Executor
Executes verified EditPlans deterministically against the Resolve editing adapter.
"""
from typing import Dict, Any, List, Optional
import time
from packages.core.models import EditPlan, OperationRecord, TimelineVerificationResult
from packages.core.validation import validate_edit_plan

class PlanExecutionError(RuntimeError):
    pass

def execute_edit_plan(plan: EditPlan, adapter: Any) -> Dict[str, Any]:
    """
    Executes an EditPlan sequentially with safety precondition checks,
    action logging, and post-execution timeline verification.
    """
    is_valid, issues = validate_edit_plan(plan)
    if not is_valid:
        raise PlanExecutionError(f"EditPlan validation failed: {'; '.join(issues)}")

    records: List[OperationRecord] = []

    def record_op(name: str, target: str, status: str, args: Dict[str, Any], res: Any = None, err: str = None):
        rec = OperationRecord(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            operation=name,
            target=target,
            status=status,
            arguments=args,
            result=res,
            error=err
        )
        records.append(rec)
        return rec

    # 1. Target Project Verification
    try:
        active_proj = adapter.get_current_project_name()
        if active_proj != plan.project_name:
            # Switch or create
            projects = adapter.list_projects()
            if plan.project_name in projects:
                adapter.load_project(plan.project_name)
                record_op("load_project", plan.project_name, "PASS", {})
            else:
                adapter.create_project(plan.project_name)
                record_op("create_project", plan.project_name, "PASS", {})

        # Safety assertion: active project MUST match
        active = adapter.get_current_project_name()
        if active != plan.project_name:
            raise PlanExecutionError(f"CRITICAL SAFETY ABORT: Active project is '{active}', expected '{plan.project_name}'. Refusing to proceed!")

    except Exception as e:
        record_op("target_project", plan.project_name, "FAILED", {}, err=str(e))
        raise PlanExecutionError(f"Failed to target project '{plan.project_name}': {e}") from e

    # 2. Import Media Assets
    imported_clips = {}
    for asset_path in plan.source_assets:
        try:
            clip = adapter.import_media(asset_path)
            imported_clips[asset_path] = clip
            record_op("import_media", asset_path, "PASS", {"path": asset_path})
        except Exception as e:
            record_op("import_media", asset_path, "FAILED", {"path": asset_path}, err=str(e))
            raise PlanExecutionError(f"Failed to import media '{asset_path}': {e}") from e

    # 3. Create or Select Timeline
    try:
        tl = adapter.ensure_timeline(plan.timeline_name, fps=plan.target_fps)
        record_op("ensure_timeline", plan.timeline_name, "PASS", {"fps": plan.target_fps})
    except Exception as e:
        record_op("ensure_timeline", plan.timeline_name, "FAILED", {"timeline": plan.timeline_name}, err=str(e))
        raise PlanExecutionError(f"Failed to create/select timeline '{plan.timeline_name}': {e}") from e

    # 4. Execute Actions
    for i, action in enumerate(plan.actions):
        try:
            clip = imported_clips.get(action.source_clip)
            if not clip:
                raise ValueError(f"Clip not imported for source: '{action.source_clip}'")

            adapter.append_clip(
                clip=clip,
                start_frame=action.start_frame,
                end_frame=action.end_frame,
                track_type=action.track_type,
                track_index=action.track_index
            )
            record_op(f"action_{action.action_type}", f"Track {action.track_type} {action.track_index}", "PASS", action.to_dict())
        except Exception as e:
            record_op(f"action_{action.action_type}", f"Track {action.track_type} {action.track_index}", "FAILED", action.to_dict(), err=str(e))
            raise PlanExecutionError(f"Action #{i} failed: {e}") from e

    # 5. Save Project
    try:
        adapter.save_project()
        record_op("save_project", plan.project_name, "PASS", {})
    except Exception as e:
        record_op("save_project", plan.project_name, "FAILED", {}, err=str(e))

    # 6. Verify Timeline
    verification = adapter.verify_timeline(plan.timeline_name)
    record_op("verify_timeline", plan.timeline_name, "PASS" if verification.verified else "FAILED", verification.to_dict())

    return {
        "status": "PASS" if verification.verified else "VERIFICATION_FAILED",
        "project": plan.project_name,
        "timeline": plan.timeline_name,
        "actions_executed": len(plan.actions),
        "verification": verification.to_dict(),
        "operations": [r.to_dict() for r in records]
    }
