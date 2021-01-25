# Test cases for genalog.text.ner_label.propagate_label_to_ocr() method.
# For READABILITY purpose, ground truth and noisy text are presented as
# a whole string, not in their tokenized format.

# Notice the `propagate_label_to_ocr()` method has the contract of
# (list, list, list) -> (list, list, list)
# consuming both ground truth text and noisy text as lists of tokens.
# We will use `genalog.text.preprocess.tokenize()` to tokenize these strings
from genalog.text import preprocess

ner_labels = []
gt_txt = []
ns_txt = []
desired_ocr_labels = []

# Alignment is one-to-one
ner_labels.append(["B-PLACE", "I-PLACE"])
gt_txt.append("New York")
ns_txt.append("New York")
desired_ocr_labels.append(["B-PLACE", "I-PLACE"])

# Alignment is one-to-many
ner_labels.append(["B-PLACE", "I-PLACE"])
gt_txt.append("New York")
ns_txt.append("N ew York")
desired_ocr_labels.append(["B-PLACE", "I-PLACE", "I-PLACE"])

# Trailing B-Labels
ner_labels.append(["B-PLACE", "I-PLACE", "O", "B-PLACE", "O", "B-PLACE"])
gt_txt.append("New York , Boston , Sidney")
ns_txt.append("N ew York Boston Sidney")
desired_ocr_labels.append(["B-PLACE", "I-PLACE", "I-PLACE", "B-PLACE", "B-PLACE"])

# Alignment is many-to-one
ner_labels.append(["B-PLACE", "I-PLACE"])
gt_txt.append("New York")
ns_txt.append("NewYork")
desired_ocr_labels.append(["B-PLACE"])

# Alignment is many-to-many
ner_labels.append(["B-PLACE", "I-PLACE", "O", "O"])
gt_txt.append("New York is big")
ns_txt.append("N ewYorkis big")
desired_ocr_labels.append(["B-PLACE", "I-PLACE", "O"])

# Missing tokens (I-label)
ner_labels.append(["B-PLACE", "I-PLACE", "V", "O"])
gt_txt.append("New York is big")
ns_txt.append("New  is big")
desired_ocr_labels.append(["B-PLACE", "V", "O"])

# Missing tokens (B-label)
ner_labels.append(["B-PLACE", "I-PLACE", "V", "O"])
gt_txt.append("New York is big")
ns_txt.append(" York is big")
desired_ocr_labels.append(["B-PLACE", "V", "O"])

ner_labels.append(["O", "O", "B-PLACE"])
gt_txt.append("This is home")
ns_txt.append("Th isis ho me")
desired_ocr_labels.append(["O", "O", "B-PLACE", "I-PLACE"])

# Missing tokens + many-to-many
ner_labels.append(["B-PLACE", "I-PLACE", "O", "O"])
gt_txt.append("New York is big")
ns_txt.append("N ewYo rkis big")
desired_ocr_labels.append(["B-PLACE", "I-PLACE", "I-PLACE", "O"])

# Missing tokens + many-to-many
ner_labels.append(["B-PLACE", "O", "O"])
gt_txt.append("Boston is big ")
ns_txt.append("B oston bi g")
desired_ocr_labels.append(["B-PLACE", "I-PLACE", "O", "O"])

# Single char tokens
ner_labels.append(["O", "O", "B-PLACE"])
gt_txt.append("a big city")
ns_txt.append("abigcity")
desired_ocr_labels.append(["O"])

# Splitted into single-char token
ner_labels.append(["O", "O", "B-PLACE"])
gt_txt.append("a big city")
ns_txt.append("abig c it y")
desired_ocr_labels.append(["O", "B-PLACE", "I-PLACE", "I-PLACE"])

# Tokens with repeating characters
ner_labels.append(["O", "FRUIT"])
gt_txt.append("an apple")
ns_txt.append("aa aaple")
desired_ocr_labels.append(["O", "FRUIT"])

# Tokens with regex special characters
ner_labels.append(["O", "FRUIT", "O"])
gt_txt.append("an apple .*/")
ns_txt.append("@n @ @p|e *. |")
desired_ocr_labels.append(["O", "FRUIT", "FRUIT", "O", "O"])

# Tokens with regex special characters with B-labels
ner_labels.append(["O", "B-FRUIT", "O"])
gt_txt.append("an apple .*/")
ns_txt.append("@n @ @p|e *. |")
desired_ocr_labels.append(["O", "B-FRUIT", "I-FRUIT", "O", "O"])

# Tokens with regex special characters in BOTH clean and noisy text
ner_labels.append(["O", "O", "ENTERTAINMENT", "O"])
gt_txt.append("@ new TV !")
ns_txt.append("@ n ow T\\/ |")
desired_ocr_labels.append(["O", "O", "O", "ENTERTAINMENT", "O"])

# Tokenize ground truth and noisy text strings
gt_tokens = [preprocess.tokenize(txt) for txt in gt_txt]
ns_tokens = [preprocess.tokenize(txt) for txt in ns_txt]

# test function expect params in tuple of
# (gt_label, gt_tokens, ocr_tokens, desired_ocr_labels)
LABEL_PROPAGATION_REGRESSION_TEST_CASES = list(
    zip(ner_labels, gt_tokens, ns_tokens, desired_ocr_labels)
)
