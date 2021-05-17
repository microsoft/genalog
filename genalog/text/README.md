## Text Alignment

This is module for common text alignment task between two strings. `genalog` provides two methods of alignment:
1. `genalog.text.anchor.align_w_anchor()`
1. `genalog.text.alignment.align()`

`align_w_anchor()` implements the Recursive Text Alignment Scheme (RETAS) from the paper [A Fast Alignment Scheme for Automatic OCR Evaluation of Books](https://ieeexplore.ieee.org/abstract/document/6065412) and works best on longer text strings, while `align()` implement the [Needleman-Wunsch algorithm](https://en.wikipedia.org/wiki/Needleman%E2%80%93Wunsch_algorithm) and works best on shorter strings. We recommend using the `align_w_anchor()` method on inputs longer than **200 characters**. Both methods share the same function contract and are interchangeable. 

```python
from genalog.text import alignment
from genalog.text import anchor

gt_txt = "New York is big"
noise_txt = "New Yo rkis "

# These two methods are interchangeable, but work best at different character length as mentioned above
aligned_gt, aligned_noise = anchor.align_w_anchor(gt_txt, noise_txt, gap_char="@")
print(f"Aligned ground truth: {aligned_gt}")
print(f"Aligned noise:        {aligned_noise}")
# Aligned ground truth: New Yo@rk is big
# Aligned noise:        New Yo rk@is @@@

aligned_gt, aligned_noise = alignment.align(gt_txt, noise_txt, gap_char="@")
print(f"Aligned ground truth: {aligned_gt}")
print(f"Aligned noise:        {aligned_noise}")
# Aligned ground truth: New Yo@rk is big
# Aligned noise:        New Yo rk@is @@@
```

You can use the method below to parse the text alignment result to get relationship mapping between tokens in the two strings.

```python
# Process the aligned strings to find out how the tokens are related
gt_to_noise_mapping, noise_to_gt_mapping = alignment.parse_alignment(aligned_gt, aligned_noise)
print(f"gt_to_noise: {gt_to_noise_mapping}")
print(f"noise_to_gt: {noise_to_gt_mapping}")

# NOTE: 1st gt token "New" maps to noise token "New", 2nd token "Yo@rk" maps to "Yo" and "rk@is", etc ...
# gt_to_noise:          [[0], [1, 2], [2], []] 
# noise_to_gt:          [[0], [1], [1, 2], []]
# Aligned ground truth: New Yo@rk is big
# Aligned noise:        New Yo rk@is @@@
```

You can format the alignment for better debugging:

```python
# Format aligned string for better display
print(alignment._format_alignment(aligned_gt, aligned_noise))
# New Yo@rk is big
# ||||||.||.|||...
# New Yo rk@is @@@
```

## Label Propagation

This module is responsible for propagating NER labels from ground tokens to OCR tokens. 

```python
from genalog.text import ner_label
from genalog.text import preprocess

gt_txt = "New York is big"
ocr_txt = "New Yo rkis big"

# Input to the method
gt_labels = ["B-P", "I-P", "O", "O"]
gt_tokens = preprocess.tokenize(gt_txt) # tokenize into list of tokens
ocr_tokens = preprocess.tokenize(ocr_txt)
```

Use `genalog.text.ner_label.propagate_label_to_ocr()` for label propagation. This method uses `align_w_anchor()` as default.

```python
from genalog.text import ner_label

# Method returns a tuple of 4 elements (gt_tokens, gt_labels, ocr_tokens, ocr_labels, gap_char)
ocr_labels, aligned_gt, aligned_ocr, gap_char = ner_label.propagate_label_to_ocr(gt_labels, gt_tokens, ocr_tokens)
```

Please note that the returned `gap_char` is the gap character used in alignment. You will need this information for parsing the returned alignment return with `alignment.parse_alignment()`

You can format the label propagation result for better display:

```python
# Format result for display
print(ner_label.format_label_propagation(gt_tokens, gt_labels, ocr_tokens, ocr_labels, aligned_gt, aligned_ocr))

# B-P I-P  O  O   
# New York is big 
# New Yo@rk is big
# ||||||.||.||||||
# New Yo rk@is big
# New Yo  rkis big 
# B-P I-P I-P  O  
```

Or without text alignment:

```python
# Format tokens and labels
print(ner_label.format_labels(ocr_tokens, ocr_labels))

# B-P I-P  O  O   
# New York is big 
# New Yo  rkis big 
# B-P I-P I-P  O 
```


## Advance Text Alignment Configuration

We use [Biopython](https://biopython.org/)'s implementation of the Needleman-Wunsch algorithm for text alignment.
This algorithm is an exhaustive search for all possible candidates with dynamic programming. 
It produces weighted score for each candidate and returns those having the highest score. 
(**NOTE** that multiple candidates can share the same score)

This algorithm has 4 hyperparameters for tuning candidate scores:
1. **Match Reward** - how much the algorithm rewards matching characters
1. **Mismatch Penalty** - how much the algorithm penalizes mismatching characters
1. **Gap Penalty** - how much the algorithm penalizes for creating a gap with a GAP_CHAR (defaults to '@')
1. **Gap Extension Penalty** - how much the algorithm penalizes for extending a gap (ex "@@@@")

You can find the default values for these four parameters as a constant in the package:
1. `genalog.text.alignment.MATCH_REWARD`
1. `genalog.text.alignment.MISMATCH_PENALTY`
1. `genalog.text.alignment.GAP_PENALTY`
1. `genalog.text.alignment.GAP_EXT_PENALTY`
