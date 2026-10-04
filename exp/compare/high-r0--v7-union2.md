# Benchmark comparison: v7-high-b24k-r0 -> v7-union2

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-union2.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.728 | 0.773 | 0.045 | [0.035, 0.056] | 1.000 |
| topic recall (required) | 0.609 | 0.703 | 0.094 | [0.079, 0.109] | 1.000 |
| topic precision | 0.871 | 0.836 | -0.035 | [-0.046, -0.024] | 0.000 |
| narrative F1 (strict) | 0.776 | 0.795 | 0.019 | [-0.001, 0.041] | 0.970 |
| frame F1 (strict) | 0.750 | 0.784 | 0.034 | [0.018, 0.052] | 1.000 |
| evidence F1 (strict) | 0.708 | 0.772 | 0.065 | [0.048, 0.081] | 1.000 |
| population F1 (strict) | 0.859 | 0.882 | 0.022 | [-0.006, 0.054] | 0.929 |
| claim recall (required) | 0.730 | 0.801 | 0.070 | [0.055, 0.087] | 1.000 |
| claim precision | 0.887 | 0.851 | -0.035 | [-0.048, -0.024] | 0.000 |
| product F1 (strict) | 0.880 | 0.873 | -0.006 | [-0.029, 0.016] | 0.296 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.695 | 0.755 | 0.703 | 0.769 |
| discourse | 0.708 | 0.750 | 0.751 | 0.798 |
| health_dense | 0.768 | 0.805 | 0.720 | 0.776 |
| mixed | 0.719 | 0.785 | 0.710 | 0.806 |
| narrative | 0.725 | 0.773 | 0.728 | 0.810 |
| null | 0.692 | 0.688 | 1.000 | 1.000 |
| rare_label | 0.709 | 0.749 | 0.722 | 0.805 |
| synthetic | 0.714 | 0.796 | 0.846 | 0.868 |

## Items that moved most (dev split)

- c182721w0002 (health_dense): topic tp 32.0->40.0, fp 19.0->23.0, fn 21.0->13.0
- c176740w0013 (discourse): topic tp 8.0->14.0, fp 1.0->5.0, fn 12.0->6.0
- c192950w0011 (health_dense): topic tp 19.0->25.0, fp 0.0->3.0, fn 7.0->1.0
- c176979w0018 (rare_label): topic tp 12.0->17.0, fp 3.0->7.0, fn 16.0->11.0
- c186894w0008 (narrative): topic tp 18.0->24.0, fp 0.0->3.0, fn 16.0->11.0
- c190127w0009 (narrative): topic tp 12.0->18.0, fp 0.0->0.0, fn 19.0->13.0
- s-topic-boundary-vaccine-covid (synthetic): topic tp 3.0->9.0, fp 0.0->0.0, fn 9.0->3.0
- c36549w0004 (health_dense): topic tp 16.0->12.0, fp 5.0->9.0, fn 7.0->10.0
- c167673w0003 (narrative): topic tp 8.0->11.0, fp 0.0->4.0, fn 3.0->0.0
- c176604w0021 (rare_label): topic tp 13.0->18.0, fp 3.0->3.0, fn 6.0->1.0
- c179765w0001 (health_dense): topic tp 24.0->28.0, fp 0.0->3.0, fn 14.0->11.0
- c192950w0002 (health_dense): topic tp 20.0->25.0, fp 0.0->2.0, fn 9.0->6.0
- c9005w0016 (narrative): topic tp 13.0->18.0, fp 1.0->3.0, fn 6.0->3.0
- c176579w0010 (rare_label): topic tp 8.0->12.0, fp 0.0->0.0, fn 15.0->10.0
- c182604w0018 (narrative): topic tp 14.0->19.0, fp 2.0->2.0, fn 12.0->8.0
