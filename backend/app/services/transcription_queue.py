import asyncio

class MeetingTranscriptionQueue:
    def __init__(self):
        self.queues = {}

    def get_queue(self, meeting_id: str):
        if meeting_id not in self.queues:
            self.queues[meeting_id] = asyncio.Queue()
        return self.queues[meeting_id]


transcription_queue = MeetingTranscriptionQueue()