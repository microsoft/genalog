# Initializing test cases
# For extensibility, all parameters in a case are append to following arrays
gt_txt = []
ns_txt = []

aligned_gt = []
aligned_ns = []

gt_to_noise_maps = []
noise_to_gt_maps = []

# we want to be able to know which clean text token each noisy text token corresponds to:
gt_txt.append("New York is big.")
ns_txt.append("N ewYork kis big.")
# alignment should yield
aligned_gt.append("N@ew York @is big.")
aligned_ns.append("N ew@York kis big.")
gt_to_noise_maps.append(
    [
        # This shows that the first token in gt "New" maps to the
        # first ("N") and second ("ewYork") token in the noise
        [0, 1],
        [1],
        [2],
        [3],
    ]
)


noise_to_gt_maps.append(
    [
        [0],
        # Similarly, the following shows that the second token in noise "ewYork" maps to the
        # first ("New") and second ("York") token in gt
        [0, 1],
        [2],
        [3],
    ]
)

##############################################################################################

# SPECIAL CASE: noisy text does not contain sufficient whitespaces to account
#               for missing tokens
# Notice there's only 1 whitespace b/w 'oston' and 'grea'
# The ideal situation is that there are 2 whitespaces. Ex:
#            ("B oston  grea t")
ns_txt.append("B oston grea t")
gt_txt.append("Boston is great")

# Notice the alignment cannot produce additional whitespace and it can only
# extend the token 'oston' with GAP_CHAP to map to the tokens 'Boston' and 'is'
# With an additional whitespace, the alignment result can be ideal:
#                 "B oston @@ grea t@"
aligned_ns.append("B oston@@@ grea t")
aligned_gt.append("B@oston is grea@t")

gt_to_noise_maps.append([[0, 1], [1], [2, 3]])  # 'is' is also mapped to 'oston'

noise_to_gt_maps.append([[0], [0, 1], [2], [2]])  # 'oston' is to 'Boston' and 'is'
############################################################################################

# Empty Cases:
gt_txt.append("")
ns_txt.append("")
aligned_gt.append("")
aligned_ns.append("")
gt_to_noise_maps.append([])
noise_to_gt_maps.append([])

gt_txt.append("")
ns_txt.append("B")
aligned_gt.append("@")
aligned_ns.append("B")
gt_to_noise_maps.append([[]])
noise_to_gt_maps.append([[]])

gt_txt.append("B")
ns_txt.append("")
aligned_gt.append("B")
aligned_ns.append("@")
gt_to_noise_maps.append([[]])
noise_to_gt_maps.append([[]])

############################################################################################
gt_txt.append("Boston is big")
ns_txt.append("B oston bi g")

aligned_gt.append("B@oston is bi@g")
aligned_ns.append("B oston@@@ bi g")

gt_to_noise_maps.append([[0, 1], [1], [2, 3]])

noise_to_gt_maps.append([[0], [0, 1], [2], [2]])

############################################################################################
gt_txt.append("New York is big.")
ns_txt.append("NewYork big")

aligned_gt.append("New York is big.")
aligned_ns.append("New@York @@@big@")

gt_to_noise_maps.append([[0], [0], [1], [1]])

noise_to_gt_maps.append([[0, 1], [2, 3]])

#############################################################################################
gt_txt.append("politicians who lag superfluous on the")
ns_txt.append("politicians who kg superfluous on the")

aligned_gt.append("politicians who lag superfluous on the")
aligned_ns.append("politicians who @kg superfluous on the")

gt_to_noise_maps.append([[0], [1], [2], [3], [4], [5]])

noise_to_gt_maps.append([[0], [1], [2], [3], [4], [5]])

############################################################################################

gt_txt.append("farther informed on the subject.")
ns_txt.append("faithei uifoimtdon the subject")

aligned_gt.append("farther @informed on the subject.")
aligned_ns.append("faithei ui@foimtd@on the subject@")

gt_to_noise_maps.append([[0], [1], [1], [2], [3]])

noise_to_gt_maps.append([[0], [1, 2], [3], [4]])

############################################################################################

gt_txt.append("New York is big .")
ns_txt.append("New Yorkis big .")

aligned_gt.append("New York is big .")
aligned_ns.append("New York@is big .")

gt_to_noise_maps.append([[0], [1], [1], [2], [3]])

noise_to_gt_maps.append([[0], [1, 2], [3], [4]])

############################################################################################

gt_txt.append("New York is big.")
ns_txt.append("New Yo rk is big.")

aligned_gt.append("New Yo@rk is big.")
aligned_ns.append("New Yo rk is big.")

gt_to_noise_maps.append([[0], [1, 2], [3], [4]])

noise_to_gt_maps.append([[0], [1], [1], [2], [3]])

# Format tests for pytest
# Each test expect in the following format
# (aligned_gt, aligned_ns, gt_to_noise_maps, noise_to_gt_maps)
PARSE_ALIGNMENT_REGRESSION_TEST_CASES = zip(
    aligned_gt, aligned_ns, gt_to_noise_maps, noise_to_gt_maps
)
ALIGNMENT_REGRESSION_TEST_CASES = list(zip(gt_txt, ns_txt, aligned_gt, aligned_ns))
