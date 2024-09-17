import base64
import hashlib
import json
import os

import requests
import substrateinterface

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

BITTENSOR_NETWORK = "finney"
VERIFY_EXTERNAL_VALIDATOR_SUBNET = False

WEIGHTS_PATH = os.path.join(
    os.environ["VALIDATOR_PATH"], "neurons", "_validator", "proof_of_weights"
)
VALIDATOR_API_PORT = os.environ.get("VALIDATOR_API_PORT", 8080)
VALIDATOR_API_URL = os.environ.get("VALIDATOR_API_URL", "http://localhost")
LAZY_RUN = os.environ.get("LAZY_RUN", False)

RECEIPTS_PATH = os.path.join(
    os.environ["VALIDATOR_PATH"],
    "neurons",
    "_validator",
    "proof_of_weights",
    "receipts",
)


@app.get("/")
async def root():
    return {
        "message": (
            "To get a proof, use /proofs/{block_number}/{hotkey}/{miner_uid} endpoint. "
            "To get a receipt, use /receipts/{transaction_hash} endpoint."
        )
    }


@app.get("/receipts/{transaction_hash}")
async def receipt(transaction_hash: str):
    filepath = os.path.join(RECEIPTS_PATH, transaction_hash)
    if os.path.exists(filepath):
        return FileResponse(
            path=filepath, filename=transaction_hash, media_type="application/json"
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Receipt file not found",
            headers={"X-Error": "Receipt not found"},
        )


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


@app.post("/submit_inputs")
async def submit_inputs(inputs: str, signature: str, sender: str, netuid: int):
    # decode inputs and signature then verify signature
    try:
        inputs = base64.b64decode(inputs)
        signature = base64.b64decode(signature)
        public_key = substrateinterface.Keypair(ss58_address=sender)
        signature_is_valid = public_key.verify(data=inputs, signature=signature)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Signature or input error: {e}",
            headers={"X-Error": "Signature or input error"},
        )
    if not signature_is_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid signature",
            headers={"X-Error": "Invalid signature"},
        )
    # verify sender is a validator on claimed network
    if VERIFY_EXTERNAL_VALIDATOR_SUBNET:
        try:
            import bittensor

            network = bittensor.subtensor(network=BITTENSOR_NETWORK)
            metagraph = network.metagraph(netuid)
            sender_id = metagraph.hotkeys.index(sender)
            if not metagraph.validator_permit[sender_id]:
                raise Exception("Sender is not a validator on claimed network")
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="Sender is not a validator on claimed network",
                headers={"X-Error": "Invalid sender"},
            )
    # do stuff with inputs
    # transaction_hash = hashlib.sha256(inputs + signature).hexdigest()
    inputs = json.loads(inputs)
    if LAZY_RUN:
        return {"message": "Inputs submitted successfully"}
    response = requests.post(
        f"{VALIDATOR_API_URL}:{VALIDATOR_API_PORT}/pow-request",
        json=inputs,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Failed to submit inputs",
            headers={"X-Error": "Failed to submit inputs"},
        )
    return JSONResponse(content=response.json())


@app.get("/get_proof_of_weights")
async def get_proof_of_weights(transaction_hash: str):
    filename = f"{transaction_hash}.json"
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
