from app.models import Config
from app.schemas import SignalIn


class DetectionAgent:
    def should_trigger(self, signal: SignalIn, config: Config) -> bool:
        if config.services and signal.service not in config.services:
            return False
        if config.signals and signal.type not in config.signals:
            return False

        thresholds = config.thresholds or {}
        if signal.type == "error_spike":
            return signal.value >= float(thresholds.get("error_rate", 5))
        if signal.type == "latency_spike":
            return signal.value >= float(thresholds.get("latency_ms", 2000))

        return signal.value > signal.baseline
