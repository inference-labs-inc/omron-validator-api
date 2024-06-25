import os


from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

WEIGHTS_PATH = os.path.join(
    os.environ["VALIDATOR_PATH"], "neurons", "_validator", "proof_of_weights"
)


@app.get("/")
async def root():
    return {
        "message": "To get a proof, use /proofs/{block_number}/{hotkey}/{miner_uid} endpoint"
    }


@app.get("/proofs/{block_number}/{hotkey}/{miner_uid}")
async def proof(block_number: int, hotkey: str, miner_uid: int):
    filename = f"{block_number}_{hotkey}_{miner_uid}.json"
    filepath = os.path.join(WEIGHTS_PATH, filename)
    if os.path.exists(filepath):
        return FileResponse(
            path=filepath, filename=filename, media_type="application/json"
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"File not found",
            headers={"X-Error": "Such proof does not exist"},
        )
