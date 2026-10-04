# Benchmark comparison: v7-high-b24k-r0 -> v7-high-nobudget

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-high-nobudget.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.728 | 0.729 | 0.001 | [-0.015, 0.017] | 0.532 |
| topic recall (required) | 0.609 | 0.613 | 0.004 | [-0.016, 0.025] | 0.667 |
| topic precision | 0.871 | 0.864 | -0.007 | [-0.028, 0.014] | 0.237 |
| narrative F1 (strict) | 0.776 | 0.809 | 0.033 | [-0.005, 0.072] | 0.949 |
| frame F1 (strict) | 0.750 | 0.770 | 0.020 | [-0.005, 0.046] | 0.948 |
| evidence F1 (strict) | 0.708 | 0.745 | 0.037 | [0.013, 0.061] | 0.998 |
| population F1 (strict) | 0.859 | 0.825 | -0.035 | [-0.072, 0.001] | 0.030 |
| claim recall (required) | 0.730 | 0.719 | -0.011 | [-0.037, 0.012] | 0.188 |
| claim precision | 0.887 | 0.874 | -0.012 | [-0.033, 0.008] | 0.106 |
| product F1 (strict) | 0.880 | 0.884 | 0.004 | [-0.028, 0.035] | 0.619 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.695 | 0.655 | 0.703 | 0.681 |
| discourse | 0.708 | 0.746 | 0.751 | 0.685 |
| health_dense | 0.768 | 0.764 | 0.720 | 0.710 |
| mixed | 0.719 | 0.729 | 0.710 | 0.645 |
| narrative | 0.725 | 0.732 | 0.728 | 0.731 |
| null | 0.692 | 0.500 | 1.000 | 1.000 |
| rare_label | 0.709 | 0.710 | 0.722 | 0.733 |
| synthetic | 0.714 | 0.690 | 0.846 | 0.714 |

## Items that moved most (dev split)

- c182721w0002 (health_dense): topic tp 32.0->43.0, fp 19.0->9.0, fn 21.0->12.0
- c179765w0001 (health_dense): topic tp 24.0->28.0, fp 0.0->11.0, fn 14.0->12.0
- c176979w0018 (rare_label): topic tp 12.0->19.0, fp 3.0->5.0, fn 16.0->9.0
- c14596w0004 (narrative): topic tp 13.0->7.0, fp 0.0->2.0, fn 4.0->9.0
- c190279w0007 (narrative): topic tp 10.0->4.0, fp 0.0->2.0, fn 4.0->9.0
- c193025w0004 (health_dense): topic tp 16.0->9.0, fp 2.0->1.0, fn 5.0->10.0
- c28560w0006 (rare_label): topic tp 8.0->2.0, fp 0.0->1.0, fn 23.0->29.0
- c78775w0002 (narrative): topic tp 6.0->13.0, fp 0.0->1.0, fn 8.0->3.0
- c176740w0012 (discourse): topic tp 22.0->27.0, fp 3.0->2.0, fn 10.0->4.0
- c182151w0019 (narrative): topic tp 25.0->21.0, fp 4.0->1.0, fn 5.0->10.0
- c185744w0001 (rare_label): topic tp 9.0->6.0, fp 6.0->1.0, fn 8.0->11.0
- c204885w0010 (narrative): topic tp 8.0->13.0, fp 0.0->1.0, fn 10.0->5.0
- c5436w0023 (rare_label): topic tp 13.0->19.0, fp 1.0->2.0, fn 14.0->10.0
- s-topic-boundary-vaccine-covid (synthetic): topic tp 3.0->9.0, fp 0.0->0.0, fn 9.0->4.0
- c181028w0001 (narrative): topic tp 5.0->10.0, fp 2.0->2.0, fn 8.0->3.0
