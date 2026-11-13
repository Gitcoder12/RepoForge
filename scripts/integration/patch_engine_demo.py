from repoforge.patch_engine import PatchEngine


engine = PatchEngine(".")


result = engine.apply_patch(
    "test.py",
    'print("RepoForge V3")'
)


print(result)