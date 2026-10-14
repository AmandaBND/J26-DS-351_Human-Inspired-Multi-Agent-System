
from pathlib import Path
from tempfile import TemporaryDirectory
from .audio_segmentation_service import AudioSegmentationService
from .audio_conversion_service import AudioConversionService
from .audio_service import AudioService, AudioData


class AudioPreprocessingPipeline:

    def __init__(self):
        self.converter = AudioConversionService()
        self.audio_service = AudioService()

    def process(self, input_path: str) -> AudioData:
        with TemporaryDirectory() as temp_dir:
            converted_path = (
                Path(temp_dir) / "converted_audio.wav"
            )

            self.converter.convert_to_wav(
                input_path,
                str(converted_path)
            )

            return self.audio_service.load_audio(
                str(converted_path)
            )

    def process_and_segment(self,input_path: str,segment_duration: float = 10.0,overlap_duration: float = 2.0):
        
        audio = self.process(input_path)

        segmenter = AudioSegmentationService(
            segment_duration=segment_duration,
            overlap_duration=overlap_duration
        )

        return segmenter.segment_audio(audio)
