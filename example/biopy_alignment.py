from Bio import pairwise2
from Bio.pairwise2 import format_alignment

# BACKGROUND: the `pairwise2` module from Biopython provides two sequence 
# alignment algorithms: 
# 1. local alignment (Smith–Waterman) and 
# 2. global alignment (Needleman-Wunsch)
# 
# Since these two algorithms have parameters to tune how
# it is rewarding character matches and penalizing mismatches,
# the module enables pseudo-parameter overloading through the following

# You can call both the alignment algorithms as
#   pairwise2.align.localXX(...)
#   pairwise2.align.globalXX(...)

# Where XX is two-character "mode" that enable different default parameter
# tuning for the algorithm

# For more information, please see source code: 
# http://biopython.org/DIST/docs/api/Bio.pairwise2-pysrc.html

# Define two sequences to be aligned
X = "alignment"
Y = "alignrnent"

MATCH_REWARD = 2
MISMATCH_PENALTY = -1
GAP_PENALTY = -0.5
GAP_EXT_PENALTY = -0.4 # Penalty for extending a gap

# Calling local sequence alignment algorithm (Smith–Waterman) with custom match/penalty parameters
alignments_local = pairwise2.align.localms(X, Y, MATCH_REWARD, MISMATCH_PENALTY, GAP_PENALTY, GAP_EXT_PENALTY)

print("################### Local Alignment (Smith–Waterman): ###################")
# Use format_alignment method to format the alignments in the list
for a in alignments_local:
    print(format_alignment(*a))

print("################### Global Alignment (Needleman-Wunsch): ###################")
# No parameters. Identical characters have score of 1, else 0.
alignments_glob = pairwise2.align.globalxx(X, Y)

for a in alignments_glob:
    print(format_alignment(*a))