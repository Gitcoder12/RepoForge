"""Mission and long-range purpose for RepoForge."""

from __future__ import annotations

from typing import Any

PROJECT_PURPOSE = (
    "Make software creation and maintenance more accessible by reducing repetitive "
    "engineering work while keeping builders informed, responsible, and in control."
)
NORTH_STAR = (
    "A world where more people can turn ideas into useful, dependable tools—and "
    "where the benefits of technology are shared broadly rather than reserved for a few."
)
ABUNDANCE_ASPIRATION = (
    "Our long-range aspiration is a society where a person's access to food, shelter, "
    "healthcare, education, energy, knowledge, and the tools to create is not dependent "
    "on earning money. As clean energy, automation, robotics, manufacturing, and open "
    "knowledge grow, money could lose its role as the gatekeeper to basic opportunity. "
    "This is a social goal, not a technical guarantee or overnight transition."
)
MISSION_PILLARS = (
    (
        "Lower the cost of building",
        "Automate repetitive repository inspection, quality checks, maintenance planning, "
        "and bounded repairs so builders can spend more time solving meaningful problems.",
    ),
    (
        "Give every builder better tools",
        "Make professional engineering workflows more understandable and accessible to "
        "students, independent developers, small teams, and open-source communities.",
    ),
    (
        "Keep humans in control",
        "Show evidence, explain proposed changes, request approval for consequential actions, "
        "and make testing, rollback, and accountability part of the workflow.",
    ),
    (
        "Grow an open ecosystem",
        "Favor interoperability, reusable modules, transparent limitations, and tools that "
        "help other projects instead of trapping builders in a closed platform.",
    ),
    (
        "Free effort for higher purposes",
        "Turn saved time and shared productive capacity toward education, care, science, "
        "planetary resilience, creativity, and responsible space exploration.",
    ),
)


def render_why_we_build(st: Any) -> None:
    """Render RepoForge's mission page inside a Streamlit page or tab."""
    st.title("Why We Build RepoForge")
    st.subheader("Make building easier. Make the benefits of building more widely shared.")
    st.write(PROJECT_PURPOSE)
    st.info(NORTH_STAR)

    st.header("The problem we are working on")
    st.write(
        "Too much engineering time is consumed by repetitive discovery, setup, "
        "maintenance, validation, and documentation work. These costs make good "
        "software harder to create and maintain—especially for people without large "
        "teams, expensive tools, or institutional support."
    )

    st.header("Our mission pillars")
    for title, description in MISSION_PILLARS:
        with st.container(border=True):
            st.subheader(title)
            st.write(description)

    st.header("The abundance horizon")
    st.write(ABUNDANCE_ASPIRATION)
    st.write(
        "A fair transition requires more than automation: broad access, worker "
        "participation, accountable governance, ecological limits, and reliable "
        "public infrastructure all matter."
    )

    st.header("How ARK fits")
    st.write(
        "RepoForge helps people build and maintain software with less friction. ARK "
        "researches whether increasingly capable autonomous systems remain reliable, "
        "bounded, and correctable. Together, they aim to make trustworthy capability "
        "easier to create and more widely useful."
    )

    st.header("What we will not optimize for")
    st.write(
        "We are not trying to maximize automation for its own sake, remove human "
        "judgment, hide uncertainty, or make a tool appear more capable than its "
        "evidence supports. The goal is useful leverage for people—not dependency "
        "on another black box."
    )
    st.caption(
        "North star: build for people · share capability · keep agency · make time for discovery."
    )
