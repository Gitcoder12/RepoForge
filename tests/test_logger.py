from repoforge.logger import RepoForgeLogger

logger = RepoForgeLogger()

logger.start_session()

logger.info("TEST", "Hello RepoForge!")

logger.warning("TEST", "This is a warning.")

logger.error("TEST", "Something went wrong.")

with logger.timer("TEST", "Sleeping"):
    import time
    time.sleep(1)

logger.end_session()

logger.close()