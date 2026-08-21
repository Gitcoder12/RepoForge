"""
RepoForge Progress Manager V3

Tracks real-time execution progress.
"""


from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)



class ProgressManager:


    def __init__(self):

        self.progress = Progress(

            SpinnerColumn(),

            TextColumn(
                "[progress.description]{task.description}"
            ),

            BarColumn(),

            TaskProgressColumn()

        )


        self.task = None



    def start(self):

        self.progress.start()


        self.task = self.progress.add_task(

            "Starting RepoForge",

            total=100

        )



    def update(
        self,
        message,
        amount
    ):


        if self.task is None:

            return


        self.progress.update(

            self.task,

            description=message,

            advance=amount

        )



    def finish(self):

        if self.task:

            self.progress.update(

                self.task,

                completed=100,

                description="🚀 RepoForge Complete"

            )


        self.progress.stop()