from copy import deepcopy
import json
from pathlib import Path

from backend.modules.aion_business.runtime.people_pilot_action_service import PeoplePilotActionService


class _Repository:
    def load_optional_dict(self, workspace_id, key):
        return {}


class _Models:
    def resolve_model(self, runtime):
        return {"status": "unavailable"}


class _Provider:
    def __init__(self):
        self.containers = _Repository()
        self.coo_missions = _Models()


class _ConversationalModels:
    def __init__(self):
        self.prompts = []

    def resolve_model(self, runtime):
        return {"status": "selected", "provider": "local", "model": "vault-choice"}

    def _invoke(self, selection, prompt):
        request = json.loads(prompt)
        self.prompts.append(request)
        if request.get("pending_capability"):
            return json.dumps({
                "capability_id": request["pending_capability"]["id"],
                "confidence": 0.95,
                "fields": {"date": "2027-10-16"},
                "missing_fields": [],
                "user_summary": "Use the supplied day for the leave request.",
            })
        if request.get("active_person"):
            return json.dumps({
                "capability_id": "people.update_person",
                "confidence": 0.96,
                "fields": {"starting_date": "2027-10-16"},
                "missing_fields": [],
                "user_summary": "Set the employee's starting date.",
            })
        return json.dumps({
            "capability_id": "none", "confidence": 0.9, "fields": {},
            "missing_fields": [], "user_summary": "Needs active profile context.",
        })


class _ConversationalProvider(_Provider):
    def __init__(self):
        super().__init__()
        self.coo_missions = _ConversationalModels()


class _SemanticPeopleModels:
    def __init__(self):
        self.prompts = []

    def resolve_model(self, runtime):
        return {
            "status": "selected", "provider": "local", "model": "qwen3-8b-fast-local-q4",
            "source": "vault_selection",
        }

    def _invoke(self, selection, prompt):
        self.prompts.append(json.loads(prompt))
        return {
            "content": json.dumps({
                "capability_id": "people.update_person",
                "confidence": 0.98,
                "fields": {
                    "person_name": "James Double",
                    "workforce_costing_basis": "hourly",
                    "workforce_costing_base_rate": "£16",
                },
                "missing_fields": [],
                "user_summary": "Set James Double's hourly rate to £16.",
            }),
            "provider": "local_model",
            "model": "qwen3-8b-fast-local-q4",
        }


class _SemanticPeopleProvider(_Provider):
    def __init__(self):
        super().__init__()
        self.coo_missions = _SemanticPeopleModels()


class _Authority:
    def __init__(self):
        self.model = {
            "workspace_id": "home-fixed",
            "revision": 3,
            "people": [{
                "id": "person.owner", "name": "Kevin Robinson", "status": "active",
                "employment_type": "owner", "role_ids": ["role.owner_director"],
            }],
            "departments": [],
            "people_operations": {"leave_requests": [], "appraisals": [], "escalations": []},
        }

    def get(self, workspace_id):
        return deepcopy(self.model)

    def save(self, workspace_id, payload, *, expected_revision=None, changed_by="current_user"):
        assert expected_revision == self.model["revision"]
        self.model = deepcopy(payload)
        self.model["revision"] = expected_revision + 1
        return deepcopy(self.model)

    def access_decision(self, *args, **kwargs):
        return {"allowed": True}


def _service():
    authority = _Authority()
    return PeoplePilotActionService(_Provider(), authority=authority), authority


def test_people_pilot_creates_person_from_delegated_instruction():
    service, authority = _service()
    result = service.handle(
        "home-fixed",
        "Create a new employee called James Double, his email is james@example.com, mobile number is +34 600 123 456, address is 10 Main Street",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    created = authority.model["people"][-1]
    assert created["name"] == "James Double"
    assert created["email"] == "james@example.com"
    assert created["phone"] == "+34 600 123 456"
    assert created["address"] == "10 Main Street"
    assert result["action_receipt"]["external_notifications_sent"] is False


def test_people_pilot_accepts_name_directly_after_employee_noun():
    service, authority = _service()
    result = service.handle(
        "home-fixed", "Create a new employee Rebecca Newman", person_id="desktop_user",
    )

    assert result["status"] == "completed"
    assert authority.model["people"][-1]["name"] == "Rebecca Newman"


def test_people_pilot_understands_self_employed_role_and_manager_in_one_natural_message():
    service, authority = _service()
    result = service.handle(
        "home-fixed",
        "create a new self employed person called peter rabbit, his email is peter@rabbit.com, mobile number is 07758693374, he is a roofer and reports to kevin robinson",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    created = authority.model["people"][-1]
    assert created["name"] == "peter rabbit"
    assert created["employment_type"] == "self_employed"
    assert created["email"] == "peter@rabbit.com"
    assert created["phone"] == "07758693374"
    assert created["position_title"] == "roofer"
    assert created["manager_id"] == "person.owner"
    assert created["role_ids"] == ["role.self_employed_contractor"]


def test_people_pilot_safely_falls_back_when_model_declines_clear_employee_action():
    authority = _Authority()
    provider = _ConversationalProvider()
    service = PeoplePilotActionService(provider, authority=authority)

    result = service.handle(
        "home-fixed",
        "create a new employee David Bellingham, his email is david@gmail.com, his mobile number is 07758493324, he is a roofer and will report to Kevin Robinson",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    created = authority.model["people"][-1]
    assert created["position_title"] == "roofer"
    assert created["manager_id"] == "person.owner"
    assert result["plan"]["planner"]["model_required"] is True
    assert result["plan"]["planner"]["semantic_model_declined"] is True
    assert provider.coo_missions.prompts


def test_people_pilot_understands_on_currency_per_hour_in_fast_path():
    service, authority = _service()
    result = service.handle(
        "home-fixed",
        "create a new self employed person called Phillip Rowe, he is a roofer, he reports to Kevin Robinson, his email address is phillip@gmail.com, his mobile number is 07758374432, he is on £8 per hour",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    created = authority.model["people"][-1]
    assert created["employment_type"] == "self_employed"
    assert created["position_title"] == "roofer"
    assert created["manager_id"] == "person.owner"
    assert created["workforce_costing"]["basis"] == "hourly"
    assert created["workforce_costing"]["base_rate"] == 8.0


def test_people_pilot_named_rate_update_writes_record_without_employee_keyword():
    service, authority = _service()
    service.handle(
        "home-fixed", "Create a new employee David Bellingham", person_id="desktop_user",
    )

    result = service.handle(
        "home-fixed",
        "update david bellingham hourly rate to £9 per hour",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    assert result["plan"]["planner"]["source"] == "bounded_people_language_fallback"
    assert result["action_receipt"]["internal_record_changed"] is True
    saved = authority.model["people"][-1]
    assert saved["name"] == "David Bellingham"
    assert saved["workforce_costing"]["basis"] == "hourly"
    assert saved["workforce_costing"]["base_rate"] == 9.0


def test_people_pilot_field_first_rate_update_resolves_person_and_value():
    service, authority = _service()
    service.handle(
        "home-fixed", "Create a new self-employed person called James Double", person_id="desktop_user",
    )

    result = service.handle(
        "home-fixed",
        "update the hourly rate of james double to £16 per hour",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    assert result["plan"]["fields"]["person_name"] == "james double"
    saved = authority.model["people"][-1]
    assert saved["workforce_costing"]["basis"] == "hourly"
    assert saved["workforce_costing"]["base_rate"] == 16.0


def test_selected_vault_model_semantically_interprets_people_request_before_write():
    setup_service, authority = _service()
    setup_service.handle(
        "home-fixed", "Create a new self-employed person called James Double", person_id="desktop_user",
    )
    provider = _SemanticPeopleProvider()
    service = PeoplePilotActionService(provider, authority=authority)

    result = service.handle(
        "home-fixed",
        "please sort out what James earns; it should now be sixteen pounds each hour",
        person_id="desktop_user",
    )

    assert provider.coo_missions.prompts
    assert result["status"] == "completed"
    assert result["plan"]["planner"]["semantic_interpreter"] is True
    assert result["action_receipt"]["readback_verified"] is True
    assert authority.model["people"][-1]["workforce_costing"]["base_rate"] == 16.0


def test_local_runtime_content_wrapper_preserves_all_mia_employee_facts():
    class Models:
        def resolve_model(self, runtime):
            return {
                "status": "selected", "provider": "local_model",
                "model": "qwen3-8b-fast-local-q4", "source": "local_model_vault",
            }

        def _invoke(self, selection, prompt):
            return {
                "content": json.dumps({
                    "capability_id": "people.create_person",
                    "confidence": 0.95,
                    "fields": {
                        "name": "Mia Robinson",
                        "email": "mia@gmail.com",
                        "phone": "07758432245",
                        "employment_type": "employee",
                        "position_title": "Accountant",
                        "manager_name": "Kevin Robinson",
                        "workforce_costing_base_rate": "£8.50",
                    },
                    "missing_fields": ["department_name"],
                    "user_summary": "Create Mia Robinson with the supplied facts.",
                }),
                "provider": "local_model",
                "model": "qwen3-8b-fast-local-q4",
            }

    class Provider(_Provider):
        def __init__(self):
            super().__init__()
            self.coo_missions = Models()

    authority = _Authority()
    service = PeoplePilotActionService(Provider(), authority=authority)
    result = service.handle(
        "home-fixed",
        "create a new employee Mia Robinson, email address is mia@gmail.com, mobile number 07758432245, mia is an accountant, mia reports to kevin robinson, mia is on an hourly rate of £8.50 per hour",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    assert result["plan"]["planner"]["semantic_interpreter"] is True
    assert result["action_receipt"]["readback_verified"] is True
    mia = authority.model["people"][-1]
    assert mia["position_title"] == "Accountant"
    assert mia["manager_id"] == "person.owner"
    assert mia["workforce_costing"]["basis"] == "hourly"
    assert mia["workforce_costing"]["base_rate"] == 8.5


def test_model_occupation_mislabeled_as_employment_type_becomes_job_title():
    class Models:
        def resolve_model(self, runtime):
            return {
                "status": "selected", "provider": "local_model",
                "model": "qwen3-8b-fast-local-q4", "source": "local_model_vault",
            }

        def _invoke(self, selection, prompt):
            return {
                "content": json.dumps({
                    "capability_id": "people.update_person",
                    "confidence": 0.95,
                    "fields": {
                        "person_name": "Mia Robinson",
                        "employment_type": "accountant",
                        "workforce_costing_base_rate": "£8.50",
                    },
                    "missing_fields": [],
                }),
                "provider": "local_model",
                "model": "qwen3-8b-fast-local-q4",
            }

    class Provider(_Provider):
        def __init__(self):
            super().__init__()
            self.coo_missions = Models()

    authority = _Authority()
    authority.model["people"].append({
        "id": "person.mia", "name": "Mia Robinson", "status": "active",
        "employment_type": "employee", "position_title": "", "manager_id": None,
        "department_ids": [], "role_ids": ["role.employee"],
        "workforce_costing": {"basis": "hourly", "base_rate": 0},
    })
    result = PeoplePilotActionService(Provider(), authority=authority).handle(
        "home-fixed",
        "Mia Robinson is an accountant and her hourly rate is £8.50 per hour",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    mia = authority.model["people"][-1]
    assert mia["employment_type"] == "employee"
    assert mia["position_title"] == "accountant"
    assert mia["workforce_costing"]["base_rate"] == 8.5


def test_active_profile_supplies_name_omitted_by_semantic_model():
    class Models:
        def resolve_model(self, runtime):
            return {"status": "selected", "provider": "local_model", "model": "qwen", "source": "local_model_vault"}

        def _invoke(self, selection, prompt):
            return {"content": json.dumps({
                "capability_id": "people.update_person",
                "confidence": 0.95,
                "fields": {"position_title": "accountant", "workforce_costing_base_rate": "£8.50"},
                "missing_fields": ["person_name"],
            })}

    class Provider(_Provider):
        def __init__(self):
            super().__init__()
            self.coo_missions = Models()

    authority = _Authority()
    authority.model["people"].append({
        "id": "person.mia", "name": "Mia Robinson", "status": "active",
        "employment_type": "employee", "position_title": "", "manager_id": None,
        "department_ids": [], "role_ids": ["role.employee"],
        "workforce_costing": {"basis": "hourly", "base_rate": 0},
    })
    result = PeoplePilotActionService(Provider(), authority=authority).handle(
        "home-fixed", "her job title is accountant and she earns £8.50 per hour",
        person_id="desktop_user", subject_context={"person_name": "Mia Robinson"},
    )

    assert result["status"] == "completed"
    assert result["plan"]["fields"]["person_name"] == "Mia Robinson"
    assert authority.model["people"][-1]["position_title"] == "accountant"


def test_people_pilot_continues_pending_create_with_short_name_answer():
    service, authority = _service()
    first = service.handle(
        "home-fixed", "Create a new employee", person_id="desktop_user",
    )
    assert first["status"] == "needs_information"

    result = service.handle(
        "home-fixed", "Rebecca Newman", person_id="desktop_user", pending_plan=first["plan"],
    )

    assert result["status"] == "completed"
    assert result["plan"]["continued_from_pending_action"] is True
    assert authority.model["people"][-1]["name"] == "Rebecca Newman"


def test_people_pilot_can_cancel_pending_action_without_writing():
    service, authority = _service()
    first = service.handle(
        "home-fixed", "Create a new employee", person_id="desktop_user",
    )
    result = service.handle(
        "home-fixed", "cancel", person_id="desktop_user", pending_plan=first["plan"],
    )

    assert result["status"] == "cancelled"
    assert len(authority.model["people"]) == 1


def test_people_pilot_updates_recent_active_profile_from_short_follow_up():
    service, authority = _service()
    created = service.handle(
        "home-fixed", "Create a new employee Rebecca Newman", person_id="desktop_user",
    )
    assert created["status"] == "completed"

    result = service.handle(
        "home-fixed",
        "email address is beccanewman979@gmail.com",
        person_id="desktop_user",
        subject_context={"person_name": "Rebecca Newman"},
    )

    assert result["status"] == "completed"
    assert result["plan"]["continued_active_profile"] == "Rebecca Newman"
    assert authority.model["people"][-1]["email"] == "beccanewman979@gmail.com"


def test_people_pilot_clears_active_profile_without_writing():
    service, authority = _service()
    result = service.handle(
        "home-fixed", "done", person_id="desktop_user",
        subject_context={"person_name": "Rebecca Newman"},
    )

    assert result["status"] == "context_cleared"
    assert len(authority.model["people"]) == 1


def test_people_pilot_continues_common_profile_fields_without_cross_capture():
    service, authority = _service()
    service.handle(
        "home-fixed",
        "Create a new contractor James Bellamu, email address is james101@gmail.com, mobile number is 07759413567",
        person_id="desktop_user",
    )
    created = authority.model["people"][-1]
    assert created["address"] == ""

    role = service.handle(
        "home-fixed",
        "job title is a roofer, line manager is Kevin Robinson",
        person_id="desktop_user",
        subject_context={"person_name": "James Bellamu"},
    )
    assert role["status"] == "completed"
    assert authority.model["people"][-1]["position_title"] == "a roofer"

    start = service.handle(
        "home-fixed",
        "his start date will be the 16/10/2027",
        person_id="desktop_user",
        subject_context={"person_name": "James Bellamu"},
    )
    assert start["status"] == "completed"
    assert authority.model["people"][-1]["start_date"] == "2027-10-16"

    pay = service.handle(
        "home-fixed",
        "his hourly rate is 9.50 per hour",
        person_id="desktop_user",
        subject_context={"person_name": "James Bellamu"},
    )
    assert pay["status"] == "completed"
    assert authority.model["people"][-1]["workforce_costing"]["basis"] == "hourly"
    assert authority.model["people"][-1]["workforce_costing"]["base_rate"] == 9.5


def test_people_pilot_fallback_accepts_natural_start_and_pay_phrasing():
    service, authority = _service()
    service.handle(
        "home-fixed", "Create a new contractor James Bellamu", person_id="desktop_user",
    )
    context = {"person_name": "James Bellamu"}

    start = service.handle(
        "home-fixed", "he is starting the job on 16/10/2027",
        person_id="desktop_user", subject_context=context,
    )
    assert start["status"] == "completed"
    assert authority.model["people"][-1]["start_date"] == "2027-10-16"

    pay = service.handle(
        "home-fixed", "pay him £9,50 an hour",
        person_id="desktop_user", subject_context=context,
    )
    assert pay["status"] == "completed"
    assert authority.model["people"][-1]["workforce_costing"]["base_rate"] == 9.5


def test_people_pilot_uses_selected_model_for_active_profile_follow_ups():
    authority = _Authority()
    authority.model["people"].append({
        "id": "person.james", "name": "James Bellamu", "status": "active",
        "employment_type": "contractor", "role_ids": ["role.contractor"],
    })
    provider = _ConversationalProvider()
    service = PeoplePilotActionService(provider, authority=authority)

    result = service.handle(
        "home-fixed", "James will begin working with us on the sixteenth of October 2027",
        person_id="desktop_user", subject_context={"person_name": "James Bellamu"},
    )

    assert result["status"] == "completed"
    assert authority.model["people"][-1]["start_date"] == "2027-10-16"
    contextual_prompt = provider.coo_missions.prompts[-1]
    assert contextual_prompt["active_person"] == "James Bellamu"
    assert any(
        rule.startswith("Users do not need to use field labels")
        for rule in contextual_prompt["rules"]
    )


def test_people_pilot_uses_selected_model_for_conversational_pending_answers():
    authority = _Authority()
    authority.model["people"].append({
        "id": "person.rebecca", "name": "Rebecca Newman", "status": "active",
        "employment_type": "employee", "role_ids": ["role.employee"],
    })
    provider = _ConversationalProvider()
    service = PeoplePilotActionService(provider, authority=authority)

    result = service.handle(
        "home-fixed", "make that the sixteenth of October next year",
        person_id="desktop_user",
        pending_plan={
            "capability_id": "people.record_leave_request",
            "fields": {"person_name": "Rebecca Newman", "leave_type": "Annual leave"},
        },
    )

    assert result["status"] == "completed"
    leave = authority.model["people_operations"]["leave_requests"][-1]
    assert leave["start_date"] == "2027-10-16"
    assert leave["end_date"] == "2027-10-16"
    assert result["plan"]["continued_from_pending_action"] is True


def test_people_pilot_updates_extended_people_admin_fields_from_chat():
    service, authority = _service()
    service.handle(
        "home-fixed", "Create a new employee Rebecca Newman", person_id="desktop_user",
    )
    context = {"person_name": "Rebecca Newman"}

    details = service.handle(
        "home-fixed", "work location is Almeria, cost centre is Roofing", person_id="desktop_user",
        subject_context=context,
    )
    assert details["status"] == "completed"
    person = authority.model["people"][-1]
    assert person["work_location"] == "Almeria"
    assert person["cost_center"] == "Roofing"

    appraisal = service.handle(
        "home-fixed", "next appraisal is 20/11/2027", person_id="desktop_user",
        subject_context=context,
    )
    assert appraisal["status"] == "completed"
    assert authority.model["people"][-1]["next_appraisal_date"] == "2027-11-20"

    costing = service.handle(
        "home-fixed",
        "employer on-cost is 12%, monthly bonus is 100, commission is 4%, productive hours per month are 150, hours per working day are 7.5",
        person_id="desktop_user", subject_context=context,
    )
    assert costing["status"] == "completed"
    saved_costing = authority.model["people"][-1]["workforce_costing"]
    assert saved_costing["employer_on_cost_percent"] == 12
    assert saved_costing["monthly_bonus"] == 100
    assert saved_costing["commission_percent"] == 4
    assert saved_costing["productive_hours_month"] == 150
    assert saved_costing["hours_per_day"] == 7.5

    onboarding = service.handle(
        "home-fixed", "contract signed and health & safety completed", person_id="desktop_user",
        subject_context=context,
    )
    assert onboarding["status"] == "completed"
    checks = authority.model["people"][-1]["onboarding"]["checks"]
    assert checks["contract"] is True
    assert checks["health_safety"] is True


def test_people_pilot_records_leave_as_human_decision_queue():
    service, authority = _service()
    result = service.handle(
        "home-fixed",
        "Update the holiday for Kevin Robinson, he needs to take the day off on 7th October 2027",
        person_id="desktop_user",
    )

    assert result["status"] == "completed"
    leave = authority.model["people_operations"]["leave_requests"][0]
    assert leave["start_date"] == "2027-10-07"
    assert leave["end_date"] == "2027-10-07"
    assert leave["status"] == "requested"
    assert result["action_receipt"]["human_decision_required"] is True


def test_people_pilot_understands_conversational_paid_unpaid_and_sick_leave():
    service, authority = _service()
    service.handle(
        "home-fixed", "Create a new employee Rebecca Newman", person_id="desktop_user",
    )

    unpaid = service.handle(
        "home-fixed", "mark employee Rebecca Newman down as unpaid holiday on 7th October 2027",
        person_id="desktop_user",
    )
    assert unpaid["status"] == "completed"
    assert authority.model["people_operations"]["leave_requests"][-1]["leave_type"] == "Unpaid leave"

    sick = service.handle(
        "home-fixed", "Rebecca Newman is off sick on 8th October 2027",
        person_id="desktop_user",
    )
    assert sick["status"] == "completed"
    assert authority.model["people_operations"]["leave_requests"][-1]["leave_type"] == "Sick leave"


def test_people_pilot_chat_has_collapsible_plain_language_help_card():
    app_source = (Path(__file__).parents[3] / "desktop/mac/src/app.js").read_text(encoding="utf-8")

    assert 'data-aion-people-help="true"' in app_source
    assert "These are examples, not commands you must copy" in app_source
    assert "Paid holiday, unpaid leave or sickness" in app_source
    assert "data-aion-people-example" in app_source


def test_people_pilot_asks_for_missing_leave_date_without_writing():
    service, authority = _service()
    result = service.handle(
        "home-fixed", "Kevin Robinson needs some holiday", person_id="desktop_user",
    )

    assert result["status"] == "needs_information"
    assert authority.model["people_operations"]["leave_requests"] == []
    assert "first day" in result["content"]


def test_people_pilot_extracts_a_local_employee_document(tmp_path):
    service, authority = _service()
    document = tmp_path / "new-employee.txt"
    document.write_text(
        "Full name: Alice Morgan\nEmail: alice@example.com\nPhone: +34 611 222 333\nJob title: Operations Coordinator",
        encoding="utf-8",
    )

    result = service.handle(
        "home-fixed", "Add this employee to the People system", person_id="desktop_user",
        attachments=[str(document)],
    )

    assert result["status"] == "completed"
    created = authority.model["people"][-1]
    assert created["name"] == "Alice Morgan"
    assert created["email"] == "alice@example.com"
    assert result["plan"]["source_documents"] == ["new-employee.txt"]
