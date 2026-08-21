import time


class Benchmark:
    """
    Stores benchmark results for AI models.
    """

    def __init__(self):

        self.results = []

    def add_result(
        self,
        model,
        success,
        latency,
        tokens=0,
        cost=0.0,
        quality=0.0,
    ):

        self.results.append(
            {
                "model": model,
                "success": success,
                "latency": latency,
                "tokens": tokens,
                "cost": cost,
                "quality": quality,
            }
        )

    def best_latency(self):

        if not self.results:
            return None

        return min(
            self.results,
            key=lambda x: x["latency"],
        )

    def best_quality(self):

        if not self.results:
            return None

        return max(
            self.results,
            key=lambda x: x["quality"],
        )

    def summary(self):

        return self.results


if __name__ == "__main__":

    benchmark = Benchmark()

    benchmark.add_result(
        model="qwen",
        success=True,
        latency=2.1,
        tokens=1250,
        cost=0.00,
        quality=8.7,
    )

    benchmark.add_result(
        model="gpt",
        success=True,
        latency=4.3,
        tokens=1190,
        cost=0.05,
        quality=9.6,
    )

    benchmark.add_result(
        model="claude",
        success=False,
        latency=8.2,
        tokens=0,
        cost=0.00,
        quality=0.0,
    )

    print("Fastest:", benchmark.best_latency())

    print("Best Quality:", benchmark.best_quality())

    print("\nSummary")

    for result in benchmark.summary():
        print(result)
