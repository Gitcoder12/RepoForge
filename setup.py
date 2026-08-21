from setuptools import setup, find_packages

setup(
    name="repoforge",
    version="1.0.0",
    description="AI-powered repository health scanner and automation engine",
    author="You",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "repoforge=repoforge.runner:main",
            "repoforge-batch=repoforge.batch_runner:main",
        ]
    },
)