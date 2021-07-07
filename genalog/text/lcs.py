# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

class LCS:
    """ Compute the Longest Common Subsequence (LCS) of two given string."""

    def __init__(self, str_m, str_n):
        self.str_m_len = len(str_m)
        self.str_n_len = len(str_n)
        dp_table = self._construct_dp_table(str_m, str_n)
        self._lcs_len = dp_table[self.str_m_len][self.str_n_len]
        self._lcs = self._find_lcs_str(str_m, str_n, dp_table)

    def _construct_dp_table(self, str_m, str_n):
        m = self.str_m_len
        n = self.str_n_len

        # Initialize DP table
        dp = [[0 for j in range(n + 1)] for i in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                # Case 1: if char1 == char2
                if str_m[i - 1] == str_n[j - 1]:
                    dp[i][j] = 1 + dp[i - 1][j - 1]
                # Case 2: take the max of the values in the top and left cell
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp

    def _find_lcs_str(self, str_m, str_n, dp_table):
        m = self.str_m_len
        n = self.str_n_len
        lcs = ""
        while m > 0 and n > 0:
            # same char
            if str_m[m - 1] == str_n[n - 1]:
                # prepend the character
                lcs = str_m[m - 1] + lcs
                m -= 1
                n -= 1
            # top cell > left cell
            elif dp_table[m - 1][n] > dp_table[m][n - 1]:
                m -= 1
            else:
                n -= 1
        return lcs

    def get_len(self):
        return self._lcs_len

    def get_str(self):
        return self._lcs
