import numpy as np
import soundfile

from tests.constants import EXAMPLE_MEDIA_PATH
from tests.mock import Serve
from tilia.requests import Get, Post, post
from tilia.timelines.audiowave.timeline import AudioWaveTimeline


class TestNormalisedAmplitudes:
    def test_divisions_are_not_capped_by_max_divisions(self, tilia, tls):
        # example.mp3 is ~10s; at a typical sample rate that's far more
        # frames than 5000, so this width used to be clamped down to the old
        # audiowave_timeline.max_divisions setting (2500).
        post(Post.APP_MEDIA_LOAD, EXAMPLE_MEDIA_PATH)

        with Serve(Get.PLAYBACK_AREA_WIDTH, 5000):
            tl = tls.create_timeline(AudioWaveTimeline)

        # exact count isn't guaranteed (chunk size is frames // divisions,
        # so results are rounded), but it must no longer be clamped to the
        # old max_divisions=2500 cap, and should land close to the request.
        assert 5000 <= len(tl) < 5100

    def test_divisions_still_bounded_by_frame_count(self, tilia, tls, tmp_path):
        # a tiny file, so an oversized width still only produces one
        # division per frame instead of ballooning past what's decoded.
        path = tmp_path / "tiny.wav"
        soundfile.write(path, np.linspace(-1, 1, 100), samplerate=100)
        post(Post.APP_MEDIA_LOAD, str(path))

        with Serve(Get.PLAYBACK_AREA_WIDTH, 10**9):
            tl = tls.create_timeline(AudioWaveTimeline)

        assert len(tl) == 100
