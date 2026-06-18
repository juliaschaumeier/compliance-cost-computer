from __future__ import annotations

from pydantic import BaseModel


class BulkUpdateResponse(BaseModel):
    updated: int


class EditableCaseGroupRow(BaseModel):
    case_group_id: int
    process_id: int
    norm_addressee: str
    case_group: str
    description: str
    change_status: str
    addressees_current: float | None = None
    annual_frequency_current: float | None = None
    cases_current: float | None = None
    addressees_current_edited: float | None = None
    annual_frequency_current_edited: float | None = None
    cases_current_edited: float | None = None
    addressees_proposed: float | None = None
    annual_frequency_proposed: float | None = None
    cases_proposed: float | None = None
    addressees_proposed_edited: float | None = None
    annual_frequency_proposed_edited: float | None = None
    cases_proposed_edited: float | None = None
    addressees_current_effective: float | None = None
    annual_frequency_current_effective: float | None = None
    cases_current_effective: float | None = None
    addressees_proposed_effective: float | None = None
    annual_frequency_proposed_effective: float | None = None
    cases_proposed_effective: float | None = None
    case_metric_research_json: dict | list | str | None = None


class EditableCaseGroupsResponse(BaseModel):
    rows: list[EditableCaseGroupRow]


class EditableProcessStepRow(BaseModel):
    step_id: int
    case_group_id: int
    norm_addressee: str
    step: str
    description: str
    change_status: str
    time_required_in_min_a_current: float | None = None
    time_required_in_min_b_current: float | None = None
    time_required_in_min_c_current: float | None = None
    time_required_in_min_d_current: float | None = None
    expenses_current: float | None = None
    time_required_in_min_a_current_edited: float | None = None
    time_required_in_min_b_current_edited: float | None = None
    time_required_in_min_c_current_edited: float | None = None
    time_required_in_min_d_current_edited: float | None = None
    expenses_current_edited: float | None = None
    time_required_in_min_a_proposed: float | None = None
    time_required_in_min_b_proposed: float | None = None
    time_required_in_min_c_proposed: float | None = None
    time_required_in_min_d_proposed: float | None = None
    expenses_proposed: float | None = None
    time_required_in_min_a_proposed_edited: float | None = None
    time_required_in_min_b_proposed_edited: float | None = None
    time_required_in_min_c_proposed_edited: float | None = None
    time_required_in_min_d_proposed_edited: float | None = None
    expenses_proposed_edited: float | None = None
    time_required_in_min_a_current_effective: float | None = None
    time_required_in_min_b_current_effective: float | None = None
    time_required_in_min_c_current_effective: float | None = None
    time_required_in_min_d_current_effective: float | None = None
    expenses_current_effective: float | None = None
    time_required_in_min_a_proposed_effective: float | None = None
    time_required_in_min_b_proposed_effective: float | None = None
    time_required_in_min_c_proposed_effective: float | None = None
    time_required_in_min_d_proposed_effective: float | None = None
    expenses_proposed_effective: float | None = None
    role_sources_current: list[dict] | None = None
    role_sources_proposed: list[dict] | None = None
    personnel_effort_current: list[dict] | None = None
    personnel_effort_proposed: list[dict] | None = None


class EditableProcessStepsResponse(BaseModel):
    rows: list[EditableProcessStepRow]
