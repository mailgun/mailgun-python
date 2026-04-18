import mailgun.client

def boot_test() -> None:
    # This triggers the Config initialization and the __slots__ setup
    client = mailgun.client.Client(auth=("api", "key"))

if __name__ == "__main__":
    boot_test()
