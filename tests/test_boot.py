import cProfile
import pstats


class TestBootPerformance:
    def test_client_boot_profile(self) -> None:
        """
        Profile the SDK boot time.

        Placing the import INSIDE the profiled function ensures we capture
        the exact cost of Python crawling the disk to compile the modules
        (assuming this test runs in an isolated worker or as a script).
        """
        profiler = cProfile.Profile()
        profiler.enable()

        import mailgun.client

        _client = mailgun.client.Client(auth=("api", "key"))

        profiler.disable()

        stats = pstats.Stats(profiler).sort_stats("tottime")

        print("\n--- TOP 20 TIME-CONSUMING OPERATIONS ---")
        stats.print_stats(20)


if __name__ == "__main__":
    test_instance = TestBootPerformance()
    test_instance.test_client_boot_profile()
