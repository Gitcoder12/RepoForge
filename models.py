from repoforge.models import MODELS


def run_models():

    print("\n🧠 RepoForge Models")
    print("=" * 60)

    print(f'{"Alias":<20}{"Model"}')
    print("-" * 60)

    for alias, model in MODELS.items():
        print(f"{alias:<20}{model}")

    print("\nTotal Models:", len(MODELS))