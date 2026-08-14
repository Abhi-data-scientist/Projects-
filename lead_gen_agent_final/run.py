import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    # On Windows, Uvicorn's reload mode switches to a Selector event loop.
    # Playwright needs the Proactor event loop to launch its browser subprocess,
    # so running with reload=True raises NotImplementedError during crawling.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
