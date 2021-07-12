# OCR-NER Dataset Generation

```{image} static/labeled_synthetic_pipeline.png
:width: 80%
:align: center
```

If you were brought here by our paper [insert link here], you may be interested in the data preparation pipeline built with `genalog`. The figure above shows the steps involved in tranforming a Named-Entity Recognition (NER) dataset like [CoNLL 2003](https://deepai.org/dataset/conll-2003-english) with synthetic Optical Character Recognition (OCR) errors. This OCR-NER dataset is useful to train an error-prune NER model against common OCR mistakes. You can find the full dataset prepration pipeline in this [notebook](https://github.com/microsoft/genalog/blob/main/example/dataset_generation.ipynb) from our repo.

We believe this methodology of inducing OCR errors onto the dataset can be applied to other NLP tasks to improve model performance against inherent noise from OCR outputs. We welcome the community to contribute if this fits your use cases.


