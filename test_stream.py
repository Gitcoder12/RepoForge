from repoforge.stream import StreamManager


def main():

    stream = StreamManager()

    # Register tasks
    stream.add_task("Architecture", model="qwen")
    stream.add_task("Backend", model="gpt")
    stream.add_task("Frontend", model="claude")

    print("Initial")
    print(stream.statistics())
    print()

    # Architecture
    stream.start_task("Architecture", "Planning...")
    stream.complete_task("Architecture", "Done")

    # Backend
    stream.start_task("Backend", "Generating API...")
    stream.update_task("Backend", "Creating routes...")
    stream.complete_task("Backend", "Done")

    # Frontend
    stream.start_task("Frontend", "Generating UI...")
    stream.fail_task("Frontend", "Model timeout")

    stream.finish()

    print("Render")
    stream.render()

    print()

    print("Summary")
    stream.summary()

    print()

    print("Snapshot")
    print(stream.snapshot())

    print()

    print("Statistics")
    print(stream.statistics())

    print()

    print("JSON")
    print(stream.to_json())

    stream.save("logs/stream.json")

    print()
    print("Saved logs/stream.json")


if __name__ == "__main__":
    main()