import asyncio
from fractions import Fraction
from typing import Awaitable, Callable

import av
from aiortc import MediaStreamTrack
from av import AudioFrame


class PCMOutputTrack(MediaStreamTrack):
    """Paced 16 kHz mono PCM queue exposed as a WebRTC audio track."""

    kind = "audio"
    sample_rate = 16000
    frame_samples = 320
    frame_bytes = frame_samples * 2

    def __init__(self, on_drain: Callable[[int], Awaitable[None]] | None = None, max_buffer_frames: int = 150) -> None:
        super().__init__()
        self._frames: asyncio.Queue[bytes] = asyncio.Queue(maxsize=max_buffer_frames)
        self._pending = bytearray()
        self._pts = 0
        self._next_time = None
        self._turn_complete = False
        self._drain_sent = False
        self._generation = 0
        self._on_drain = on_drain

    async def push_pcm(self, data: bytes) -> None:
        self._pending.extend(data)
        while len(self._pending) >= self.frame_bytes:
            frame = bytes(self._pending[:self.frame_bytes])
            del self._pending[:self.frame_bytes]
            await self._frames.put(frame)

    def begin_turn(self, generation: int | None = None) -> None:
        self.clear(generation)

    async def mark_turn_complete(self) -> None:
        if self._pending:
            frame = bytes(self._pending) + bytes(self.frame_bytes - len(self._pending))
            self._pending.clear()
            await self._frames.put(frame)
        self._turn_complete = True
        self._notify_if_drained()

    def clear(self, generation: int | None = None) -> None:
        if generation is not None:
            self._generation = generation
        else:
            self._generation += 1
        self._pending.clear()
        while True:
            try:
                self._frames.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._turn_complete = False
        self._drain_sent = False

    def _notify_if_drained(self) -> None:
        if self._turn_complete and self._frames.empty() and not self._drain_sent:
            self._drain_sent = True
            if self._on_drain:
                asyncio.create_task(self._on_drain(self._generation))

    async def recv(self) -> AudioFrame:
        loop = asyncio.get_running_loop()
        if self._next_time is None:
            self._next_time = loop.time()
        delay = self._next_time - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)
        self._next_time = max(self._next_time + 0.02, loop.time())
        try:
            pcm = self._frames.get_nowait()
        except asyncio.QueueEmpty:
            pcm = bytes(self.frame_bytes)
        self._notify_if_drained()
        frame = AudioFrame(format="s16", layout="mono", samples=self.frame_samples)
        frame.planes[0].update(pcm)
        frame.sample_rate = self.sample_rate
        frame.pts = self._pts
        frame.time_base = Fraction(1, self.sample_rate)
        self._pts += self.frame_samples
        return frame


class PCMResampler:
    """Convert inbound WebRTC audio frames to ElevenLabs PCM 16 kHz mono."""

    def __init__(self) -> None:
        self._resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

    def convert(self, frame: AudioFrame) -> list[bytes]:
        return [bytes(out.planes[0]) for out in self._resampler.resample(frame)]
