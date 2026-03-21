from app.resilience import CircuitBreaker, FallbackReason, FALLBACK_MESSAGES


def test_circuit_starts_closed():
    cb = CircuitBreaker(threshold=3, reset_seconds=30)
    assert cb.is_open('asr') is False


def test_circuit_opens_after_threshold():
    cb = CircuitBreaker(threshold=3, reset_seconds=30)
    cb.record_failure('asr')
    cb.record_failure('asr')
    assert cb.is_open('asr') is False
    cb.record_failure('asr')
    assert cb.is_open('asr') is True   # now open


def test_circuit_independent_per_service():
    cb = CircuitBreaker(threshold=3, reset_seconds=30)
    cb.record_failure('asr')
    cb.record_failure('asr')
    cb.record_failure('asr')
    assert cb.is_open('asr') is True
    assert cb.is_open('web') is False   # web unaffected
    assert cb.is_open('tts') is False   # tts unaffected


def test_circuit_resets_on_success():
    cb = CircuitBreaker(threshold=3, reset_seconds=30)
    cb.record_failure('asr')
    cb.record_failure('asr')
    cb.record_success('asr')
    cb.record_failure('asr')
    cb.record_failure('asr')
    assert cb.is_open('asr') is False  # reset, needs 3 more failures


def test_fallback_messages_exist():
    assert FallbackReason.ASR_TIMEOUT in FALLBACK_MESSAGES
    assert FallbackReason.AGENT_TIMEOUT in FALLBACK_MESSAGES
    assert FallbackReason.TOOL_ERROR in FALLBACK_MESSAGES
    assert len(FALLBACK_MESSAGES[FallbackReason.ASR_TIMEOUT]) > 0


def test_get_status():
    cb = CircuitBreaker(threshold=3, reset_seconds=30)
    assert cb.get_status('asr') == 'closed'
    cb.record_failure('asr')
    cb.record_failure('asr')
    cb.record_failure('asr')
    assert cb.get_status('asr') == 'open'