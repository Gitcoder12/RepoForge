"""
RepoForge Quality Score Engine V4
"""


class QualityScore:


    def calculate(
        self,
        scan
    ):

        if not isinstance(
            scan,
            dict
        ):
            scan = {}


        stats = scan.get(
            "statistics",
            {}
        )


        files = stats.get(
            "files",
            0
        )


        lines = stats.get(
            "lines",
            0
        )


        languages = scan.get(
            "languages",
            {}
        )


        structure = scan.get(
            "structure",
            {}
        )


        issues = scan.get(
            "issues",
            []
        )


        score = 40


        # Repository maturity

        if files > 10:

            score += 10


        if files > 500:

            score += 10


        if lines > 10000:

            score += 10


        if lines > 100000:

            score += 10



        # Documentation

        documentation = False


        for item in structure.keys():

            name = str(
                item
            ).lower()


            if (
                "readme" in name
                or
                "docs" in name
                or
                "documentation" in name
            ):

                documentation = True

                break



        if documentation:

            score += 5



        # Language diversity

        if isinstance(
            languages,
            dict
        ):

            if len(languages) >= 2:

                score += 5



        # Tests

        tests = False


        for item in structure.keys():

            name = str(
                item
            ).lower()


            if "test" in name:

                tests = True

                break



        for issue in issues:

            if not isinstance(
                issue,
                dict
            ):

                continue


            message = str(

                issue.get(
                    "message",
                    ""
                )

            ).lower()


            if "no test" in message:

                tests = False



        if tests:

            score += 5



        # Issue penalty

        issue_count = len(
            issues
        )


        score -= min(
            issue_count * 2,
            20
        )


        score = max(
            0,
            min(
                score,
                100
            )
        )



        if score >= 90:

            grade = "A"


        elif score >= 75:

            grade = "B"


        elif score >= 60:

            grade = "C"


        elif score >= 40:

            grade = "D"


        else:

            grade = "F"



        return {

            "score": score,

            "grade": grade,

            "details": {

                "files": files,

                "lines": lines,

                "languages": len(languages)
                    if isinstance(languages, dict)
                    else 0,

                "documentation": documentation,

                "tests": tests,

                "issues": issue_count

            }

        }