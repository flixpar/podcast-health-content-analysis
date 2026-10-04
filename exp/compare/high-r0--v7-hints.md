# Benchmark comparison: v7-high-b24k-r0 -> v7-hints-llm

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-hints-llm.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.728 | 0.752 | 0.024 | [0.004, 0.043] | 0.990 |
| topic recall (required) | 0.609 | 0.663 | 0.055 | [0.026, 0.082] | 1.000 |
| topic precision | 0.871 | 0.842 | -0.029 | [-0.049, -0.010] | 0.001 |
| narrative F1 (strict) | 0.776 | 0.779 | 0.003 | [-0.036, 0.042] | 0.562 |
| frame F1 (strict) | 0.750 | 0.762 | 0.012 | [-0.013, 0.036] | 0.830 |
| evidence F1 (strict) | 0.708 | 0.741 | 0.033 | [0.007, 0.060] | 0.992 |
| population F1 (strict) | 0.859 | 0.839 | -0.020 | [-0.061, 0.021] | 0.158 |
| claim recall (required) | 0.730 | 0.699 | -0.031 | [-0.062, 0.000] | 0.024 |
| claim precision | 0.887 | 0.901 | 0.014 | [-0.005, 0.033] | 0.928 |
| product F1 (strict) | 0.880 | 0.874 | -0.005 | [-0.042, 0.028] | 0.398 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.695 | 0.721 | 0.703 | 0.714 |
| discourse | 0.708 | 0.722 | 0.751 | 0.690 |
| health_dense | 0.768 | 0.790 | 0.720 | 0.703 |
| mixed | 0.719 | 0.726 | 0.710 | 0.677 |
| narrative | 0.725 | 0.739 | 0.728 | 0.690 |
| null | 0.692 | 0.571 | 1.000 | 1.000 |
| rare_label | 0.709 | 0.754 | 0.722 | 0.696 |
| synthetic | 0.714 | 0.726 | 0.846 | 0.780 |

## Items that moved most (dev split)

- c186894w0008 (narrative): topic tp 18.0->0.0, fp 0.0->0.0, fn 16.0->34.0
- c28560w0006 (rare_label): topic tp 8.0->20.0, fp 0.0->5.0, fn 23.0->11.0
- c176979w0018 (rare_label): topic tp 12.0->24.0, fp 3.0->5.0, fn 16.0->4.0
- c176740w0013 (discourse): topic tp 8.0->14.0, fp 1.0->9.0, fn 12.0->6.0
- c206720w0004 (narrative): topic tp 10.0->0.0, fp 0.0->0.0, fn 6.0->16.0
- c182721w0002 (health_dense): topic tp 32.0->38.0, fp 19.0->13.0, fn 21.0->14.0
- c179765w0001 (health_dense): topic tp 24.0->33.0, fp 0.0->3.0, fn 14.0->8.0
- c190127w0009 (narrative): topic tp 12.0->20.0, fp 0.0->2.0, fn 19.0->11.0
- c190550w0001 (health_dense): topic tp 12.0->21.0, fp 0.0->1.0, fn 9.0->4.0
- s-topic-boundary-vaccine-covid (synthetic): topic tp 3.0->10.0, fp 0.0->1.0, fn 9.0->2.0
- c182151w0019 (narrative): topic tp 25.0->16.0, fp 4.0->3.0, fn 5.0->9.0
- c176579w0010 (rare_label): topic tp 8.0->14.0, fp 0.0->0.0, fn 15.0->8.0
- c190406w0003 (narrative): topic tp 6.0->0.0, fp 1.0->0.0, fn 5.0->11.0
- c192950w0002 (health_dense): topic tp 20.0->16.0, fp 0.0->5.0, fn 9.0->13.0
- c177172w0003 (health_dense): topic tp 11.0->16.0, fp 3.0->5.0, fn 13.0->8.0
