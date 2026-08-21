from collections import Counter


class AIReviewer:
    """
    Reviews executor outputs before merging.
    """

    def review(self, results):

        report = {
            "success": True,
            "issues": [],
            "summary": {},
        }

        if not results:
            report["success"] = False
            report["issues"].append(
                "No results were produced."
            )
            return report

        completed = 0
        failed = 0

        tasks = []

        for result in results:

            task = result.get("task", "unknown")
            tasks.append(task)

            response = result.get("response", "")

            if result.get("success"):

                completed += 1

                if not response.strip():

                    report["issues"].append(
                        f"{task}: Empty response."
                    )

                elif len(response.strip()) < 50:

                    report["issues"].append(
                        f"{task}: Response is very short."
                    )

            else:

                failed += 1

                report["issues"].append(
                    f"{task}: {response}"
                )

        duplicates = [

            task

            for task, count in Counter(tasks).items()

            if count > 1

        ]

        if duplicates:

            report["issues"].append(

                f"Duplicate tasks: {', '.join(duplicates)}"

            )

        report["summary"] = {

            "completed": completed,

            "failed": failed,

            "total": len(results),

        }

        if failed > 0:

            report["success"] = False

        return report


if __name__ == "__main__":

    reviewer = AIReviewer()

    sample = [

        {
            "task": "backend",
            "success": True,
            "response": "Backend completed successfully."
        },

        {
            "task": "frontend",
            "success": True,
            "response": "Frontend completed successfully."
        },

        {
            "task": "database",
            "success": False,
            "response": "Connection timeout."
        },

    ]

    report = reviewer.review(sample)

    print(report)