"""Model selection compatibility for the pinned Batchalign 0.7.21.post11.

Its ASR constructor ignores explicit model IDs. Initialize its backing fields here
so generation stays upstream, without modifying installed dependency files.
"""
import batchalign as ba
from batchalign.models import BertCantoneseUtteranceModel, BertUtteranceModel, resolve
import pycountry


class WhisperModel(ba.WhisperASRModel):
    """Keep Batchalign's timestamp parsing while supporting English-only Whisper."""

    def __init__(self, model, base, language):
        """Load weights and matching tokenizer/config once for the chosen model."""
        super().__init__(model, base=base, language=language)
        self._pipeline = self.pipe
        # Upstream always sends language/task, which English-only Whisper rejects.
        self.pipe = self._generate

    def _generate(self, data, *, batch_size, generate_kwargs):
        """Remove multilingual options only when the model declares English-only."""
        options = dict(generate_kwargs)
        config = options['generation_config']
        if getattr(config, 'is_multilingual', True) is False:
            if self.lang.lower() != 'english':
                raise ValueError("The selected English-only model requires English audio.")
            options.pop('language', None)
            options.pop('task', None)
        return self._pipeline(data, batch_size=batch_size, generate_kwargs=options)


class WhisperEngine(ba.WhisperEngine):
    """Honor explicit Whisper choices and preserve Batchalign's language defaults."""

    def __init__(self, model=None, lang='eng'):
        """Select matching artifacts and initialize upstream generation state."""
        default = resolve('whisper', lang) or ('openai/whisper-large-v3', 'openai/whisper-large-v3')
        self.model_name = model if model is not None else default[0]
        # Known Batchalign fine-tunes intentionally use their pretrained base's
        # tokenizer/config. Other selections use their own artifacts, never v3's.
        base = default[1] if self.model_name == default[0] else self.model_name
        language = 'Malay' if lang == 'mys' else pycountry.languages.get(alpha_3=lang).name
        if language == 'Yue Chinese':
            language = 'Cantonese'
        if 'greek' in language.lower():
            language = 'Greek'

        # These private field names are the compatibility boundary with the pinned
        # Batchalign version. Inherited generate()/tasks use them directly.
        self.whisper_model = WhisperModel(self.model_name, base=base, language=language)
        self._WhisperEngine__whisper = self.whisper_model
        self._WhisperEngine__lang = lang
        utterance_model = resolve('utterance', lang)
        self._WhisperEngine__engine = None
        if utterance_model is not None:
            utterance_type = BertCantoneseUtteranceModel if lang == 'yue' else BertUtteranceModel
            self._WhisperEngine__engine = utterance_type(utterance_model)


class WhisperUTREngine(ba.WhisperUTREngine):
    """Recover utterance timings using the already loaded ASR model."""

    def __init__(self, asr: WhisperEngine, lang='eng'):
        """Share the timestamp-capable backend instead of loading another model."""
        # ASR already requires timestamp output. The same model therefore supports
        # upstream timing recovery; its constructor would load a second large model
        # even on transcripts where process() immediately skips existing timings.
        self._WhisperUTREngine__whisper = asr.whisper_model
        self._WhisperUTREngine__lang = lang
