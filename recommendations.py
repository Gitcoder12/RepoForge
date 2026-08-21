"""
RepoForge Recommendation Engine V2

Ranks repository improvements.
"""


from typing import Dict, Any, List



class RecommendationEngine:
    """
    Generates prioritized engineering recommendations.
    """



    def generate(
        self,
        intelligence: Dict[str, Any],
    ) -> List[Dict[str, Any]]:


        recommendations = []


        quality = intelligence.get(
            "quality",
            {}
        )


        improvements = quality.get(
            "improvements",
            []
        )


        for item in improvements:


            recommendations.append(

                {

                    "title":
                        item,


                    "impact":
                        self.impact(
                            item
                        ),


                    "priority":
                        self.priority(
                            item
                        ),


                    "priority_score":
                        self.priority(
                            item
                        ),


                    "difficulty":
                        self.difficulty(
                            item
                        ),

                }

            )



        if not recommendations:


            recommendations.append(

                {

                    "title":
                        "Repository is healthy",


                    "impact":
                        "low",


                    "priority":
                        "maintenance",


                    "priority_score":
                        10,


                    "difficulty":
                        "easy",

                }

            )



        return sorted(

            recommendations,

            key=lambda x: x["priority_score"],

            reverse=True,

        )



    def impact(
        self,
        issue: str,
    ) -> str:


        text = issue.lower()



        if "security" in text:

            return "critical"



        if "test" in text:

            return "high"



        if "readme" in text or "documentation" in text:

            return "medium"



        return "low"



    def priority(
        self,
        issue: str,
    ) -> int:


        text = issue.lower()



        if "security" in text:

            return 100



        if "test" in text:

            return 80



        if "readme" in text:

            return 50



        if "documentation" in text:

            return 50



        return 30



    def difficulty(
        self,
        issue: str,
    ) -> str:


        text = issue.lower()



        if "architecture" in text:

            return "hard"



        if "test" in text:

            return "medium"



        return "easy"