# Benchmark comparison: v7-refine -> v7-glm-refine-ds

Paired bootstrap over 304 item-repeat rows (304 shared items); positive delta favours v7-glm-refine-ds.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.782 | 0.794 | 0.012 | [-0.001, 0.025] | 0.962 |
| topic recall (required) | 0.718 | 0.720 | 0.002 | [-0.016, 0.023] | 0.562 |
| topic precision | 0.838 | 0.863 | 0.025 | [0.009, 0.041] | 0.999 |
| narrative F1 (strict) | 0.811 | 0.806 | -0.005 | [-0.033, 0.022] | 0.367 |
| frame F1 (strict) | 0.774 | 0.799 | 0.025 | [0.005, 0.043] | 0.995 |
| evidence F1 (strict) | 0.770 | 0.778 | 0.008 | [-0.008, 0.024] | 0.829 |
| population F1 (strict) | 0.874 | 0.875 | 0.001 | [-0.031, 0.032] | 0.515 |
| claim recall (required) | 0.823 | 0.826 | 0.004 | [-0.011, 0.018] | 0.675 |
| claim precision | 0.839 | 0.862 | 0.023 | [0.011, 0.036] | 1.000 |
| product F1 (strict) | 0.880 | 0.909 | 0.028 | [0.002, 0.057] | 0.982 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.765 | 0.809 | 0.769 | 0.824 |
| discourse | 0.750 | 0.781 | 0.836 | 0.812 |
| health_dense | 0.818 | 0.833 | 0.816 | 0.818 |
| mixed | 0.744 | 0.778 | 0.839 | 0.742 |
| narrative | 0.786 | 0.793 | 0.831 | 0.837 |
| null | 0.545 | 0.606 | 1.000 | 1.000 |
| rare_label | 0.769 | 0.773 | 0.810 | 0.824 |
| synthetic | 0.768 | 0.762 | 0.901 | 0.868 |

## Items that moved most (dev split)

- c182721w0002 (health_dense): topic tp 40.0->44.0, fp 26.0->15.0, fn 13.0->9.0
- c179765w0001 (health_dense): topic tp 33.0->25.0, fp 2.0->0.0, fn 7.0->14.0
- c186894w0008 (narrative): topic tp 29.0->22.0, fp 6.0->2.0, fn 7.0->12.0
- c331394w0027 (narrative): topic tp 12.0->8.0, fp 0.0->7.0, fn 0.0->3.0
- c176579w0010 (rare_label): topic tp 8.0->14.0, fp 1.0->1.0, fn 15.0->8.0
- c177018w0009 (rare_label): topic tp 23.0->17.0, fp 1.0->0.0, fn 5.0->11.0
- c4171w0010 (rare_label): topic tp 0.0->5.0, fp 0.0->2.0, fn 6.0->1.0
- c182305w0009 (rare_label): topic tp 18.0->13.0, fp 3.0->0.0, fn 5.0->8.0
- c78786w0019 (narrative): topic tp 18.0->14.0, fp 5.0->2.0, fn 2.0->6.0
- c177172w0003 (health_dense): topic tp 11.0->16.0, fp 4.0->4.0, fn 13.0->8.0
- c181028w0001 (narrative): topic tp 5.0->10.0, fp 2.0->2.0, fn 8.0->3.0
- c318639w0005 (discourse): topic tp 5.0->10.0, fp 0.0->0.0, fn 7.0->2.0
- c180821w0010 (rare_label): topic tp 12.0->16.0, fp 4.0->2.0, fn 5.0->2.0
- c78775w0002 (narrative): topic tp 7.0->11.0, fp 1.0->1.0, fn 8.0->3.0
- c181249w0003 (health_dense): topic tp 27.0->24.0, fp 3.0->3.0, fn 3.0->8.0
