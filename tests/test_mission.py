from repoforge.mission import (
    ABUNDANCE_ASPIRATION,
    MISSION_PILLARS,
    NORTH_STAR,
    PROJECT_PURPOSE,
)


def test_repoforge_mission_centres_accessible_software_building():
    assert "software creation and maintenance" in PROJECT_PURPOSE
    assert "accessible" in PROJECT_PURPOSE
    assert "in control" in PROJECT_PURPOSE


def test_abundance_vision_is_an_aspiration_not_a_guarantee():
    assert "not dependent on earning money" in ABUNDANCE_ASPIRATION
    assert "not a technical guarantee" in ABUNDANCE_ASPIRATION
    assert "governance" in ABUNDANCE_ASPIRATION


def test_shared_north_star_and_pillars_are_present():
    assert "benefits of technology are shared" in NORTH_STAR
    assert len(MISSION_PILLARS) >= 5
    assert any("space exploration" in description for _, description in MISSION_PILLARS)
