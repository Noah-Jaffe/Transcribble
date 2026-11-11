"""Exercise installed Batchalign behavior without downloading model artifacts."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import torch
from batchalign.models.whisper import infer_asr
from src import Whisper


class WhisperSelectionTests(unittest.TestCase):
    def setUp(self):
        """Intercept every artifact loader used by the real Whisper constructor."""
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.config = SimpleNamespace(is_multilingual=False)
        self.load_config = self.stack.enter_context(patch.object(
            infer_asr.GenerationConfig, 'from_pretrained', return_value=self.config))
        self.tokenizer = self.stack.enter_context(patch.object(infer_asr.WhisperTokenizer, 'from_pretrained'))
        self.processor = self.stack.enter_context(patch.object(infer_asr.WhisperProcessor, 'from_pretrained'))
        self.pipeline = self.stack.enter_context(patch.object(infer_asr, 'pipeline'))
        self.pipeline.return_value.return_value = {
            'chunks': [{'text': 'Hello world.', 'timestamp': (0.0, 1.0)}]}
        self.stack.enter_context(patch.object(Whisper, 'BertUtteranceModel'))
        self.stack.enter_context(patch.object(Whisper, 'BertCantoneseUtteranceModel'))

    def test_explicit_model_controls_weights_and_all_base_artifacts(self):
        """Selecting tiny.en must never load the default large model's artifacts."""
        engine = Whisper.WhisperEngine('openai/whisper-tiny.en')
        self.assertEqual(engine.model_name, 'openai/whisper-tiny.en')
        self.assertEqual(self.pipeline.call_args.kwargs['model'], 'openai/whisper-tiny.en')
        self.load_config.assert_called_once_with('openai/whisper-tiny.en')
        self.tokenizer.assert_called_once_with('openai/whisper-tiny.en')
        self.processor.assert_called_once_with('openai/whisper-tiny.en')
        self.pipeline.assert_called_once()

    def test_default_finetune_keeps_matching_base_artifacts(self):
        """An omitted selection preserves Batchalign's known model/base pairing."""
        engine = Whisper.WhisperEngine()
        self.assertEqual(engine.model_name, 'talkbank/CHATWhisper-en')
        self.assertEqual(self.pipeline.call_args.kwargs['model'], engine.model_name)
        self.load_config.assert_called_once_with('openai/whisper-large-v2')

    def test_english_only_inference_removes_language_and_task(self):
        """Use upstream parsing with valid English-only generation arguments."""
        engine = Whisper.WhisperEngine('openai/whisper-tiny.en')
        result = engine.whisper_model(torch.zeros(16000))
        options = self.pipeline.return_value.call_args.kwargs['generate_kwargs']
        self.assertNotIn('language', options)
        self.assertNotIn('task', options)
        self.assertEqual(options['generation_config'], self.config)
        self.assertTrue(result['monologues'][0]['elements'])
        self.assertTrue(self.pipeline.call_args.kwargs['return_timestamps'])

    def test_multilingual_inference_preserves_requested_language(self):
        """A multilingual selection keeps the task and requested language."""
        self.config.is_multilingual = True
        engine = Whisper.WhisperEngine('openai/whisper-tiny', lang='spa')
        engine.whisper_model(torch.zeros(16000))
        options = self.pipeline.return_value.call_args.kwargs['generate_kwargs']
        self.assertEqual(options['language'], 'Spanish')
        self.assertEqual(options['task'], 'transcribe')
        self.load_config.assert_called_once_with('openai/whisper-tiny')

    def test_english_only_model_rejects_other_languages(self):
        """An incompatible language must not silently change the selected model."""
        engine = Whisper.WhisperEngine('openai/whisper-tiny.en', lang='spa')
        with self.assertRaisesRegex(ValueError, 'requires English'):
            engine.whisper_model(torch.zeros(16000))
        self.pipeline.return_value.assert_not_called()

    def test_inherited_generation_uses_selected_backend(self):
        """Verify compatibility fields against the real upstream generate method."""
        from batchalign.pipelines.asr import whisper as upstream
        engine = Whisper.WhisperEngine('openai/whisper-tiny.en')
        doc = Mock()
        with patch.object(engine.whisper_model, 'load') as load, patch.object(
            upstream, 'process_generation', return_value=doc
        ) as process, patch.object(upstream, 'correct_timing', return_value=doc):
            load.return_value.all.return_value = torch.zeros(16000)
            self.assertIs(engine.generate('audio.wav'), doc)
        self.assertEqual(process.call_args.args[1], 'eng')
        self.assertEqual(doc.media.url, 'audio.wav')
        self.assertIn(Whisper.ba.Task.ASR, engine.tasks)


if __name__ == '__main__':
    unittest.main()
