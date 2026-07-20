from fastapi import FastAPI, HTTPException, Depends
from mailgun.client import AsyncClient
from mailgun.handlers.error_handler import ApiError
from mailgun.ext.pydantic.models import SendMessageSchema

app = FastAPI()


# 1. Dependency Injection for the Client Lifecycle
async def get_mailgun_client():
    # 2. Enable dry_run=True so it mocks the network locally!
    async with AsyncClient(auth=("api", "my-key"), dry_run=True) as client:
        yield client


@app.post("/send-email")
async def send_email(
    payload: SendMessageSchema, mailgun_client: AsyncClient = Depends(get_mailgun_client)
):
    clean_data = payload.model_dump(by_alias=True, exclude_none=True)

    try:
        response = await mailgun_client.messages.create(domain="my-domain.com", data=clean_data)
        return response.json()

    except ApiError as e:
        # 3. Gracefully handle actual Mailgun network/auth errors
        raise HTTPException(status_code=400, detail=str(e))
