"""Check pipeline model wiring without model downloads or output files."""
from contextlib import ExitStack
import unittest
from unittest.mock import Mock, patch

import transcribe_proc as proc


class TranscriptionModelWiringTests(unittest.TestCase):
    def test_single_speaker_skips_unused_engines(self):
        """Single-speaker jobs share Whisper and never construct disabled engines."""
        self.check_pipeline(1)

    def test_multiple_speakers_enable_diarization_once(self):
        """Multiple-speaker jobs construct and execute one diarization stage."""
        self.check_pipeline(2)

    def check_pipeline(self, speakers):
        """Record constructors and stages for one side-effect-free transcription."""
        with ExitStack() as stack:
            stack.enter_context(patch.object(proc, 'debug_get_version', return_value='test'))
            stack.enter_context(patch.object(proc.os.path, 'exists', return_value=False))
            stack.enter_context(patch.object(proc.ba.Document, 'new'))
            stack.enter_context(patch.object(proc.ba, 'CHATFile'))
            stack.enter_context(patch.object(proc.ba, 'WhisperEngine', side_effect=AssertionError('ignored selection')))
            stack.enter_context(patch.object(proc.ba, 'WhisperUTREngine', side_effect=AssertionError('duplicate model')))
            asr = stack.enter_context(patch.object(proc, 'WhisperEngine'))
            utr = stack.enter_context(patch.object(proc, 'WhisperUTREngine'))
            diarization = stack.enter_context(patch.object(proc.ba, 'NemoSpeakerEngine'))
            stanza = stack.enter_context(patch.object(proc.ba, 'StanzaEngine'))
            disfluency = stack.enter_context(patch.object(proc.ba, 'DisfluencyReplacementEngine'))
            retrace = stack.enter_context(patch.object(proc.ba, 'NgramRetraceEngine'))
            alignment = stack.enter_context(patch.object(proc.ba, 'Wave2VecFAEngine'))
            pipeline = stack.enter_context(patch.object(proc.ba, 'BatchalignPipeline'))
            stack.enter_context(patch('builtins.print'))
            result = proc.transcribe_file(
                'audio.wav', model_name='openai/whisper-tiny.en', num_speakers=speakers,
                lang='eng', open_after=False, debug=False,
            )
        self.assertEqual(result, 'audio.wav.cha')
        asr.assert_called_once_with(model='openai/whisper-tiny.en', lang='eng')
        utr.assert_called_once_with(asr.return_value, lang='eng')
        stanza.assert_not_called()
        expected = [asr.return_value]
        if speakers > 1:
            diarization.assert_called_once_with(num_speakers=speakers)
            expected.append(diarization.return_value)
        else:
            diarization.assert_not_called()
        expected += [disfluency.return_value, retrace.return_value, utr.return_value, alignment.return_value]
        self.assertEqual([call.args[0] for call in pipeline.call_args_list], expected)


if __name__ == '__main__':
    unittest.main()
