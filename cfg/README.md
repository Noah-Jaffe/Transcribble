### cfg/models.json
Contains a list of objects, where each object is a huggingface search query. This is what is used to populate the list of available models.

Valid keys are:
| Key 	| Description 	|
|---	|---	|
| search	| Text search. 	|
| author	| Filter from the given author. 	|
| filter	| Filter based on tags, such as text-classification or spacy. 	|
| limit	| Max number of results. (1 thru 1000)	|
| inference_provider	| Filter based on the available [inference providers](https://huggingface.co/docs/huggingface_hub/en/guides/inference#supported-providers-and-tasks) for the model. 	|

For example,
[The equivalent to this search](https://huggingface.co/api/models?search=whisper&author=openai&limit=3&full=false&config=true) would be the following:
```
{"author": "openai", "search": "whisper", limit: "3"}
```

<br>

[See here for more options](https://huggingface.co/models?pipeline_tag=automatic-speech-recognition&library=transformers&sort=trending)

### mascot.png
An image to display while the work is in progress.

### cache.json
Default cache options to use for each Transcriber user.