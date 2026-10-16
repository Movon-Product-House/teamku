from movon_hr.modules.attendance.rules import allowed_check_in_radius_meters, haversine_meters
from movon_hr.seed import OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_RADIUS_METERS


def test_haversine_returns_zero_at_same_point() -> None:
    assert (
        haversine_meters(OFFICE_LATITUDE, OFFICE_LONGITUDE, OFFICE_LATITUDE, OFFICE_LONGITUDE) == 0
    )


def test_haversine_finds_nearby_point() -> None:
    assert 100 < haversine_meters(OFFICE_LATITUDE, OFFICE_LONGITUDE, -6.201, OFFICE_LONGITUDE) < 120


def test_accuracy_credit_is_capped_to_prevent_home_check_in() -> None:
    assert allowed_check_in_radius_meters(OFFICE_RADIUS_METERS, 10) == OFFICE_RADIUS_METERS + 10
    assert allowed_check_in_radius_meters(OFFICE_RADIUS_METERS, 500) == OFFICE_RADIUS_METERS + 50
