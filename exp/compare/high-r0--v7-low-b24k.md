# Benchmark comparison: v7-high-b24k-r0 -> v7-low-b24k

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-low-b24k.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.728 | 0.675 | -0.053 | [-0.074, -0.033] | 0.000 |
| topic recall (required) | 0.609 | 0.535 | -0.073 | [-0.098, -0.049] | 0.000 |
| topic precision | 0.871 | 0.868 | -0.003 | [-0.025, 0.019] | 0.399 |
| narrative F1 (strict) | 0.776 | 0.762 | -0.014 | [-0.049, 0.021] | 0.217 |
| frame F1 (strict) | 0.750 | 0.715 | -0.035 | [-0.059, -0.010] | 0.002 |
| evidence F1 (strict) | 0.708 | 0.687 | -0.020 | [-0.046, 0.006] | 0.061 |
| population F1 (strict) | 0.859 | 0.793 | -0.067 | [-0.115, -0.019] | 0.003 |
| claim recall (required) | 0.730 | 0.661 | -0.070 | [-0.101, -0.042] | 0.000 |
| claim precision | 0.887 | 0.893 | 0.006 | [-0.012, 0.025] | 0.762 |
| product F1 (strict) | 0.880 | 0.870 | -0.010 | [-0.042, 0.019] | 0.255 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.695 | 0.730 | 0.703 | 0.637 |
| discourse | 0.708 | 0.678 | 0.751 | 0.690 |
| health_dense | 0.768 | 0.732 | 0.720 | 0.672 |
| mixed | 0.719 | 0.663 | 0.710 | 0.742 |
| narrative | 0.725 | 0.629 | 0.728 | 0.639 |
| null | 0.692 | 0.560 | 1.000 | 1.000 |
| rare_label | 0.709 | 0.672 | 0.722 | 0.683 |
| synthetic | 0.714 | 0.597 | 0.846 | 0.538 |

## Items that moved most (dev split)

- c182721w0002 (health_dense): topic tp 32.0->42.0, fp 19.0->9.0, fn 21.0->13.0
- c190127w0009 (narrative): topic tp 12.0->0.0, fp 0.0->0.0, fn 19.0->31.0
- c193025w0004 (health_dense): topic tp 16.0->5.0, fp 2.0->0.0, fn 5.0->13.0
- c9834w0016 (narrative): topic tp 17.0->7.0, fp 0.0->1.0, fn 2.0->11.0
- c176979w0018 (rare_label): topic tp 12.0->20.0, fp 3.0->4.0, fn 16.0->8.0
- c179765w0002 (health_dense): topic tp 20.0->13.0, fp 2.0->0.0, fn 4.0->11.0
- c178189w0009 (narrative): topic tp 14.0->8.0, fp 0.0->2.0, fn 10.0->17.0
- c189960w0013 (health_dense): topic tp 11.0->4.0, fp 0.0->0.0, fn 2.0->8.0
- c28560w0006 (rare_label): topic tp 8.0->2.0, fp 0.0->1.0, fn 23.0->29.0
- c175341w0013 (rare_label): topic tp 14.0->10.0, fp 5.0->1.0, fn 6.0->9.0
- c186894w0008 (narrative): topic tp 18.0->13.0, fp 0.0->1.0, fn 16.0->21.0
- c190279w0007 (narrative): topic tp 10.0->4.0, fp 0.0->0.0, fn 4.0->9.0
- c192950w0002 (health_dense): topic tp 20.0->15.0, fp 0.0->0.0, fn 9.0->15.0
- c192950w0011 (health_dense): topic tp 19.0->13.0, fp 0.0->0.0, fn 7.0->12.0
- c206720w0004 (narrative): topic tp 10.0->5.0, fp 0.0->1.0, fn 6.0->11.0
