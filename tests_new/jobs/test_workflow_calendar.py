"""Workflows calendar (/admin/tasks/?view=calendar): the launches API and setting a launch from it."""
import datetime

import pytest

from app import db
from app.core.db_class.task_scheduler import AdminWorkflow, AdminWorkflowRun
from tests_new.helpers.access import FORBIDDEN, LOGIN, OK, assert_outcome, matrix

ADMIN_ONLY = {"anonymous": LOGIN, "user": FORBIDDEN, "owner": FORBIDDEN, "admin": OK}


def _workflow(client, title="Night"):
    uuid = client.post("/admin/tasks/workflows/create", json={"title": title, "description": "keep me"}).get_json()["workflow"]["uuid"]
    client.post("/admin/tasks/create", json={"workflow_uuid": uuid, "title": "Caches", "task_type": "clear_caches",
                                              "trigger_mode": "once", "run_once_at": "2099-01-01T00:00:00Z"})
    return uuid


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_calendar_is_admin_only(role, expected, clients):
    assert_outcome(clients[role].get("/admin/tasks/calendar"), expected)


@pytest.mark.parametrize("role, expected", matrix(ADMIN_ONLY))
def test_setting_a_launch_is_admin_only(role, expected, clients):
    uuid = _workflow(clients["admin"])
    response = clients[role].post(f"/admin/tasks/workflows/{uuid}/launch",
                                  json={"launch": {"trigger_mode": "daily", "hour": 2, "minute": 0}})
    assert_outcome(response, expected)


def test_weekly_launch_shows_every_week_in_the_users_time_zone(clients):
    admin = clients["admin"]
    uuid = _workflow(admin)

    response = admin.post(f"/admin/tasks/workflows/{uuid}/launch", json={"launch": {
        "trigger_mode": "weekly", "days_of_week": [1], "hour": 3, "minute": 30, "timezone": "Europe/Paris"}})

    assert response.status_code == 200
    events = [e for e in admin.get("/admin/tasks/calendar").get_json()["events"] if e["kind"] == "planned"]
    assert len(events) >= 4
    assert all(datetime.datetime.fromisoformat(e["start"]).weekday() == 1 for e in events)
    assert AdminWorkflow.query.filter_by(uuid=uuid).first().description == "keep me"   # only the launch changed


def test_bad_launch_is_refused(clients):
    uuid = _workflow(clients["admin"])
    response = clients["admin"].post(f"/admin/tasks/workflows/{uuid}/launch",
                                     json={"launch": {"trigger_mode": "weekly", "days_of_week": [9]}})
    assert response.status_code == 400


def test_past_launches_are_shown(clients):
    admin = clients["admin"]
    uuid = _workflow(admin)
    wf = AdminWorkflow.query.filter_by(uuid=uuid).first()
    db.session.add(AdminWorkflowRun(uuid="run-1", workflow_id=wf.id,
                                    started_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)))
    db.session.commit()

    events = admin.get("/admin/tasks/calendar").get_json()["events"]

    assert any(e["kind"] == "past" and e["run_uuid"] == "run-1" for e in events)


def test_no_more_than_the_daily_limit(clients):
    admin = clients["admin"]
    day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    statuses = []
    for n in range(6):
        uuid = _workflow(admin, title=f"W{n}")
        statuses.append(admin.post(f"/admin/tasks/workflows/{uuid}/launch",
                                   json={"launch": {"trigger_mode": "once", "run_once_at": f"{day}T0{n}:00:00Z"}}).status_code)
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 400                     # the 6th launch that day is refused


def test_colour_and_icon_kept_and_checked(clients):
    admin = clients["admin"]
    w = admin.post("/admin/tasks/workflows/create",
                   json={"title": "Night", "color": "#AbCdEf", "icon": "fa-database"}).get_json()["workflow"]
    assert (w["color"], w["icon"]) == ("#abcdef", "fa-database")
    w = admin.post(f"/admin/tasks/workflows/{w['uuid']}/update",
                   json={"title": "Night", "color": "red;", "icon": "<b>x</b>"}).get_json()["workflow"]
    assert (w["color"], w["icon"]) == (None, None)
