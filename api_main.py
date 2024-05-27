from telethon import TelegramClient, events, sync
from fastapi import FastAPI, Request, UploadFile, File, Form
import asyncio
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import time
import os
from fastapi.responses import StreamingResponse


api_id = 21749585
api_hash = os.getenv("API_HASH")
username = os.getenv("USERNAME")
phone = os.getenv("PHONE")

client = TelegramClient(username, api_id, api_hash)
app = FastAPI()

origins = [
    "http://localhost:3000", 
    "https://colab-dev.com", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await client.start(phone=phone)
    print("Connected!")

@app.get("/")
async def read_root(request: Request):
    message_id = 797
    message = await client.get_messages("me", ids=message_id)

    if message.media:
        file_path = await client.download_media(message=message.media)
        return FileResponse(file_path, filename=file_path.split("/")[-1])
    else:
        return {"message": "No media in this message"}


# Progress callback
def callback(current, total, label="Completed"):
    print(
        label,
        current,
        "out of",
        total,
        "bytes: {:.2%}".format(current / total),
    )


@app.post("/upload")
async def upload_file(request: Request, username: str = Form(...), file: UploadFile = File(...)):
    # print(file)
    file_path = file.filename
    file_content = await file.read()
    if len(file_content) > 2 * 1024 * 1024 * 1024:
        return {"error": "File size exceeds 2GB limit"}

    message = await client.send_file(
        "me",
        file_content,
        caption=f"{file.filename}",
        # force_document=True,
        progress_callback=callback,
    )

    return {"url": f"http://localhost:8000/download_offset/{username}/{message.id}"}


@app.get("/download_offset/{username}/{message_id}")
async def read_root(request: Request, message_id: int = 0, username: str = None):
    # message_id = 797
    message = await client.get_messages("me", ids=message_id)
    message_content = message.text

    if message.media:

        async def generate():
            yield await client.download_media(
                message, file=bytes, progress_callback=callback
            )

        return StreamingResponse(
            generate(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={message_content}"},
        )
    else:
        return {"message": "No media in this message"}


@app.get("/force_disconnect")
async def disconnect():
    await client.disconnect()
    return {"message": "Disconnected!"}


@app.on_event("shutdown")
async def shutdown_event():
    await client.disconnect()
    print("Disconnected!")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
