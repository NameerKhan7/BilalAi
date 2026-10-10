"""Shared temporal acceptance rule for live audio and regression playback."""
from collections import deque

class DetectionGate:
    def __init__(self, threshold, consecutive_frames=2, cooldown_seconds=.6):
        if not 0 < threshold < 1:
            raise ValueError('threshold must be between 0 and 1')
        if consecutive_frames < 1:
            raise ValueError('consecutive_frames must be positive')
        self.threshold = threshold
        self.consecutive_frames = consecutive_frames
        self.cooldown_seconds = cooldown_seconds
        self.reset()

    def reset(self):
        self.scores = deque(maxlen=self.consecutive_frames)
        self.last_hit = float('-inf')
        self.armed = True

    def update(self, score, now):
        self.scores.append(float(score))
        if score < self.threshold:
            self.armed = True
        stable = min(self.scores) if len(self.scores) == self.consecutive_frames else 0.0
        detected = self.armed and stable >= self.threshold and now-self.last_hit >= self.cooldown_seconds
        if detected:
            self.last_hit = now
            self.armed = False
        return bool(detected), float(stable)
