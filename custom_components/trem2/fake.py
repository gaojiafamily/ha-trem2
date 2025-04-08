"""TEST Server."""

import random
from threading import Thread
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

content = []


class State:
    """State."""

    def __init__(self) -> None:
        """Initialize the state."""
        self.eq_id = 1140000

    def update_eq_id(self, new_value):
        """Update the eq_id."""
        self.eq_id = new_value


def publish_earthquake_data() -> int:
    """Publish earthquake data."""
    state = State()
    time.sleep(15)
    state.update_eq_id(state.eq_id + 1)
    earthquake_data = {
        "id": state.eq_id,
        "author": "測試資料",
        "serial": 1,
        "final": 0,
        "eq": {
            "lat": 24.03,
            "lon": 122.16,
            "depth": 40,
            "loc": "花蓮縣外海",
            "mag": 6.2,
            "time": int((time.time() - 15) * 1000),
            "max": 4,
        },
        "time": int(time.time() * 1000),
    }
    content.append(earthquake_data)
    while True:
        time.sleep(random.uniform(2, 3))

        earthquake_data["serial"] += 1
        earthquake_data["eq"]["mag"] += random.uniform(-0.05, 0.1)
        earthquake_data["eq"]["mag"] = round(earthquake_data["eq"]["mag"], 1)
        earthquake_data["eq"]["depth"] += random.randint(-1, 3) * 10
        earthquake_data["eq"]["lat"] += random.uniform(-0.2, 0.1)
        earthquake_data["eq"]["lon"] += random.uniform(-0.2, 0.1)
        earthquake_data["eq"]["lat"] = round(earthquake_data["eq"]["lat"], 2)
        earthquake_data["eq"]["lon"] = round(earthquake_data["eq"]["lon"], 2)
        earthquake_data["eq"]["depth"] = max(10, earthquake_data["eq"]["depth"])
        current_time = int(time.time() * 1000)
        earthquake_data["time"] = current_time
        if earthquake_data["serial"] >= 3:
            earthquake_data["final"] = 1
            break
    time.sleep(180)
    content.pop(0)


@app.get("/api/v2/eq/eew")
async def get_earthquake():
    """Resp data."""
    return JSONResponse(content=content)


@app.get("/post")
async def post_earthquake():
    """Publish earthquake."""
    update_thread = Thread(target=publish_earthquake_data)
    update_thread.start()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
