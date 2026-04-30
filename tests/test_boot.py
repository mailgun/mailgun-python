# tests/test_boot.py
import cProfile
import pstats

def boot_test() -> None:
    # Placing the import INSIDE the profiled function ensures we capture
    # the exact cost of Python crawling the disk to compile the modules.
    import mailgun.client
    _client = mailgun.client.Client(auth=("api", "key"))

if __name__ == "__main__":
    profiler = cProfile.Profile()

    profiler.enable()
    boot_test()
    profiler.disable()

    # Sort by 'tottime' (Total internal time) and print the top 20 offenders
    stats = pstats.Stats(profiler).sort_stats('tottime')

    print("\n--- TOP 20 TIME-CONSUMING OPERATIONS ---")
    stats.print_stats(20)
