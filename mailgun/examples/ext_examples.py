from fastapi import FastAPI, HTTPException, Depends
from mailgun.client import AsyncClient
from mailgun.handlers.error_handler import ApiError
from mailgun.ext.pydantic.models import SendMessageSchema
from pydantic import ValidationError

app = FastAPI()


# 1. Dependency Injection for the Client Lifecycle
async def get_mailgun_client():
    # 2. Enable dry_run=True so it mocks the network locally!
    async with AsyncClient(auth=("api", "my-key"), dry_run=True) as client:
        yield client


# JSON example to test in http://127.0.0.1:8000/docs#/default/send_email_send_email_post
# {
#   "to": ["user@example.com"],
#   "from": "admin@company.com",
#   "subject": "Weekly Report",
#   "text": "Here is your report.",
#   "custom_params": {
#     "v:invoice_id": "99824",
#     "h:X-Priority": "High",
#     "o:tracking": "yes"
#   }
# }
@app.post("/send-email")
async def send_email(
    payload: SendMessageSchema, mailgun_client: AsyncClient = Depends(get_mailgun_client)
):
    # Use a serializer to flatten custom_params and exclude None values
    clean_data = payload.to_mailgun_payload()

    try:
        response = await mailgun_client.messages.create(domain="my-domain.com", data=clean_data)
        return response.json()

    except ApiError as e:
        # 3. Gracefully handle actual Mailgun network/auth errors
        raise HTTPException(status_code=400, detail=str(e))


def test_validation():
    print("--- 1. Testing Valid Payload ---")
    try:
        valid_payload = SendMessageSchema(
            from_="admin@company.com",
            to=["user@example.com"],
            subject="Weekly Report",
            text="Here is your report.",
        )
        print("✅ Valid payload passed validation!")
        print(f"Data: {valid_payload.to_mailgun_payload()}")
    except ValidationError as e:
        print(f"❌ Valid payload failed: {e}")

    print("\n--- 2. Testing Invalid Email ---")
    try:
        SendMessageSchema(
            from_="admin@company.com",
            to=["bad-email-format"],  # Missing @
            subject="Test",
            text="Content",
        )
    except ValidationError as e:
        print(f"✅ Caught expected error (Invalid email):")
        print(e.json())

    print("\n--- 3. Testing Missing Content ---")
    try:
        SendMessageSchema(from_="admin@company.com", to=["user@example.com"], subject="Empty body")
    except ValidationError as e:
        print(f"✅ Caught expected error (Missing content):")
        print(e.json())

    print("\n--- 4. Testing Custom Variables (v: and h:) ---")
    try:
        # Use custom_params instead of **kwargs to ensure security and validation
        var_payload = SendMessageSchema(
            from_="admin@company.com",
            to=["user@example.com"],
            text="Variables test",
            custom_params={"v:my_var": "123", "h:X-Custom-Header": "Value"},
        )
        print("✅ Custom variables/headers accepted!")
        print(f"Flattened payload: {var_payload.to_mailgun_payload()}")
    except ValidationError as e:
        print(f"❌ Custom variables failed: {e}")


if __name__ == "__main__":
    test_validation()
