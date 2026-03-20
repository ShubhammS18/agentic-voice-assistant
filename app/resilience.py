import time
from enum import Enum
from collections import defaultdict


class FallbackReason(str, Enum):
    
    ASR_TIMEOUT = "asr_timeout"
    LLM_TIMEOUT = "llm_timeout"
    TTS_TIMEOUT = "tts_timeout"
    EMPTY_AUDIO = "empty_audio"
    AGENT_TIMEOUT = "agent_timeout"
    TOOL_ERROR = "tool_error"


FALLBACK_MESSAGES = {
    FallbackReason.ASR_TIMEOUT:   "I did not catch that. Could you repeat?",
    FallbackReason.LLM_TIMEOUT:   "I am taking longer than expected. Please try again.",
    FallbackReason.TTS_TIMEOUT:   "I had trouble generating audio. Please try again.",
    FallbackReason.EMPTY_AUDIO:   "I did not detect any audio. Please try again.",
    FallbackReason.AGENT_TIMEOUT: "I am still deciding how to answer that. Please try again.",
    FallbackReason.TOOL_ERROR:    "I had trouble accessing that information. Please try again."}


class CircuitBreaker:
    """
    Tracks failures per service independently.
    After threshold consecutive failures, circuit opens and
    the service is skipped until reset_seconds has elapsed.
    """

    def __init__(self, threshold: int = 3, reset_seconds: int = 30):
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self._failures: dict[str, int] = defaultdict(int)
        self._opened_at: dict[str, float] = {}

    def is_open(self, service: str) -> bool:
        if service not in self._opened_at:
            return False
        elapsed = time.time() - self._opened_at[service]
        if elapsed > self.reset_seconds:
            # Auto-reset after reset_seconds
            self._failures[service] = 0
            del self._opened_at[service]
            print(f'[circuit] {service} circuit reset after {elapsed:.0f}s')
            return False
        return True

    def record_failure(self, service: str):
        self._failures[service] += 1
        print(f'[circuit] {service} failure #{self._failures[service]}')
        if self._failures[service] >= self.threshold:
            self._opened_at[service] = time.time()
            print(f'[circuit] {service} circuit OPENED after {self.threshold} failures')

    def record_success(self, service: str):
        if self._failures[service] > 0:
            self._failures[service] = 0
            self._opened_at.pop(service, None)
            print(f'[circuit] {service} circuit reset on success')

    def get_status(self, service: str) -> str:
        return "open" if self.is_open(service) else "closed"


# Single shared instance used across the application
circuit_breaker = CircuitBreaker()