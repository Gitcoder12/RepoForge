"""
RepoForge Intelligence Engine V3

Combines repository understanding systems.
"""


from typing import Dict, Any


from repoforge.intelligence.quality_score import QualityScore
from repoforge.intelligence.repository_map import RepositoryMap
from repoforge.intelligence.dependency_graph import DependencyGraph
from repoforge.intelligence.recommendations import RecommendationEngine
from repoforge.intelligence.score_engine import ScoreEngine



class IntelligenceEngine:
    """
    Complete repository intelligence layer.
    """


    def __init__(
        self,
        repo_path: str,
    ):

        self.repo_path = repo_path

        self.quality = QualityScore()

        self.score_engine = ScoreEngine()

        self.repository_map = RepositoryMap(
            repo_path
        )

        self.dependencies = DependencyGraph(
            repo_path
        )

        self.recommendations = RecommendationEngine()



    def analyze(
        self,
        scan: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:


        scan = scan or {}


        quality_result = self.quality.calculate(
            scan
        )


        score_result = self.score_engine.calculate(
            scan
        )


        final_score = score_result.get(
            "score",
            quality_result.get(
                "score",
                0
            )
        )


        final_grade = score_result.get(
            "grade",
            quality_result.get(
                "grade",
                "N/A"
            )
        )



        intelligence = {


            "repository":

                self.repo_path,


            "quality_score": {
                "score": final_score,
                "grade": final_grade,
                "quality_details": quality_result.get("details", {}),
                "breakdown": score_result.get("breakdown", {}),
                "signals": score_result.get("signals", {}),
            },



            "architecture":

                self.repository_map.build(),



            "dependencies":

                self.dependencies.build(),



            "status":

                "ready"

        }



        intelligence["recommendations"] = (

            self.recommendations.generate(
                intelligence
            )

        )


        return intelligence