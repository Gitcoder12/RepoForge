class AIDiscussion:
    """
    Coordinates discussion between AI agents.

    Current Version:
    - Collects all outputs
    - Detects failures
    - Decides whether another discussion round is needed

    Future Version:
    - Models critique each other
    - Models revise answers
    - Consensus building
    """

    def discuss(
        self,
        execution_plan,
        results,
        review,
    ):

        discussion = {
            "continue": False,
            "round": execution_plan.discussion_rounds,
            "feedback": [],
        }

        if not review["success"]:

            discussion["continue"] = True

            for issue in review["issues"]:

                discussion["feedback"].append(
                    issue
                )

            return discussion

        if execution_plan.review:

            discussion["feedback"].append(
                "Review completed successfully."
            )

        if execution_plan.discussion_rounds > 0:

            discussion["feedback"].append(
                "Consensus reached."
            )

        return discussion


if __name__ == "__main__":

    from repoforge.strategist import AIStrategist
    from repoforge.reviewer import AIReviewer

    strategist = AIStrategist()
    reviewer = AIReviewer()

    plan = strategist.create_plan(
        "Build a Netflix clone"
    )

    sample = [

        {
            "task": "backend",
            "success": True,
            "response": "Backend complete."
        },

        {
            "task": "frontend",
            "success": False,
            "response": "Frontend failed."
        },

    ]

    report = reviewer.review(sample)

    discussion = AIDiscussion().discuss(
        plan,
        sample,
        report,
    )

    print(discussion)