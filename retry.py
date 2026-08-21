class RetryEngine:
    """
    Handles retries and fallback models.
    """

    def __init__(self):

        self.max_retries = 2

    def should_retry(
        self,
        result,
    ):

        return not result.get(
            "success",
            False,
        )

    def retries(self):

        return self.max_retries


if __name__ == "__main__":

    retry = RetryEngine()

    print(retry.should_retry({
        "success": False
    }))

    print(retry.retries())