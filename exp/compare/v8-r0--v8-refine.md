# Benchmark comparison: v8-high-b24k-r0 -> v8-refine

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v8-refine.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.660 | 0.706 | 0.046 | [0.035, 0.058] | 1.000 |
| topic recall (required) | 0.545 | 0.622 | 0.078 | [0.063, 0.093] | 1.000 |
| topic precision | 0.805 | 0.789 | -0.016 | [-0.028, -0.004] | 0.007 |
| narrative F1 (strict) | 0.708 | 0.756 | 0.049 | [0.021, 0.078] | 1.000 |
| frame F1 (strict) | 0.716 | 0.764 | 0.049 | [0.030, 0.068] | 1.000 |
| evidence F1 (strict) | 0.675 | 0.731 | 0.056 | [0.035, 0.076] | 1.000 |
| population F1 (strict) | 0.814 | 0.806 | -0.008 | [-0.039, 0.024] | 0.336 |
| claim recall (required) | 0.648 | 0.748 | 0.100 | [0.081, 0.124] | 1.000 |
| claim precision | 0.928 | 0.885 | -0.043 | [-0.055, -0.032] | 0.000 |
| product F1 (strict) | 0.869 | 0.908 | 0.039 | [0.014, 0.071] | 0.999 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.724 | 0.725 | 0.593 | 0.648 |
| discourse | 0.650 | 0.704 | 0.610 | 0.704 |
| health_dense | 0.692 | 0.739 | 0.676 | 0.754 |
| mixed | 0.615 | 0.640 | 0.484 | 0.548 |
| narrative | 0.658 | 0.702 | 0.650 | 0.769 |
| null | 0.210 | 0.200 | 1.000 | 1.000 |
| rare_label | 0.635 | 0.693 | 0.642 | 0.750 |
| synthetic | 0.649 | 0.688 | 0.703 | 0.802 |

## Items that moved most (dev split)

- c186894w0008 (narrative): topic tp 0.0->17.0, fp 0.0->7.0, fn 34.0->18.0
- c176604w0021 (rare_label): topic tp 6.0->13.0, fp 2.0->4.0, fn 11.0->5.0
- c28560w0006 (rare_label): topic tp 1.0->8.0, fp 1.0->1.0, fn 30.0->23.0
- c182151w0019 (narrative): topic tp 16.0->24.0, fp 6.0->10.0, fn 8.0->7.0
- c182721w0002 (health_dense): topic tp 43.0->48.0, fp 24.0->27.0, fn 11.0->6.0
- c190127w0009 (narrative): topic tp 18.0->25.0, fp 1.0->2.0, fn 13.0->8.0
- c179765w0001 (health_dense): topic tp 22.0->24.0, fp 11.0->3.0, fn 19.0->17.0
- c174981w0008 (narrative): topic tp 15.0->19.0, fp 5.0->8.0, fn 14.0->10.0
- c29445w0004 (discourse): topic tp 7.0->12.0, fp 1.0->0.0, fn 6.0->1.0
- c36549w0004 (health_dense): topic tp 15.0->20.0, fp 8.0->10.0, fn 10.0->7.0
- c185664w0014 (health_dense): topic tp 8.0->11.0, fp 1.0->4.0, fn 7.0->4.0
- c169519w0002 (narrative): topic tp 8.0->10.0, fp 2.0->6.0, fn 7.0->5.0
- c177018w0009 (rare_label): topic tp 18.0->23.0, fp 4.0->4.0, fn 10.0->7.0
- c179765w0002 (health_dense): topic tp 14.0->18.0, fp 0.0->0.0, fn 10.0->6.0
- c190168w0014 (narrative): topic tp 11.0->13.0, fp 3.0->7.0, fn 6.0->4.0
