# Benchmark comparison: v7-high-b24k-r0 -> v7-glm53-b24k

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-glm53-b24k.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.728 | 0.732 | 0.004 | [-0.023, 0.028] | 0.608 |
| topic recall (required) | 0.609 | 0.612 | 0.004 | [-0.029, 0.038] | 0.570 |
| topic precision | 0.871 | 0.875 | 0.003 | [-0.020, 0.026] | 0.618 |
| narrative F1 (strict) | 0.776 | 0.752 | -0.024 | [-0.065, 0.015] | 0.117 |
| frame F1 (strict) | 0.750 | 0.717 | -0.033 | [-0.065, -0.003] | 0.018 |
| evidence F1 (strict) | 0.708 | 0.680 | -0.027 | [-0.060, 0.006] | 0.046 |
| population F1 (strict) | 0.859 | 0.804 | -0.055 | [-0.096, -0.014] | 0.006 |
| claim recall (required) | 0.730 | 0.683 | -0.047 | [-0.078, -0.019] | 0.001 |
| claim precision | 0.887 | 0.923 | 0.036 | [0.017, 0.056] | 1.000 |
| product F1 (strict) | 0.880 | 0.847 | -0.033 | [-0.073, 0.004] | 0.042 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.695 | 0.741 | 0.703 | 0.736 |
| discourse | 0.708 | 0.764 | 0.751 | 0.676 |
| health_dense | 0.768 | 0.759 | 0.720 | 0.670 |
| mixed | 0.719 | 0.663 | 0.710 | 0.645 |
| narrative | 0.725 | 0.708 | 0.728 | 0.694 |
| null | 0.692 | 0.593 | 1.000 | 1.000 |
| rare_label | 0.709 | 0.734 | 0.722 | 0.667 |
| synthetic | 0.714 | 0.730 | 0.846 | 0.747 |

## Items that moved most (dev split)

- c28560w0006 (rare_label): topic tp 8.0->27.0, fp 0.0->1.0, fn 23.0->4.0
- c190562w0004 (health_dense): topic tp 18.0->0.0, fp 2.0->0.0, fn 3.0->21.0
- c174925w0002 (health_dense): topic tp 16.0->0.0, fp 6.0->0.0, fn 14.0->29.0
- c175129w0004 (narrative): topic tp 11.0->0.0, fp 2.0->0.0, fn 3.0->13.0
- c182721w0002 (health_dense): topic tp 32.0->36.0, fp 19.0->8.0, fn 21.0->16.0
- c176979w0018 (rare_label): topic tp 12.0->21.0, fp 3.0->2.0, fn 16.0->7.0
- c174981w0008 (narrative): topic tp 23.0->15.0, fp 4.0->3.0, fn 6.0->14.0
- c179765w0001 (health_dense): topic tp 24.0->32.0, fp 0.0->2.0, fn 14.0->8.0
- c176556w0004 (narrative): topic tp 17.0->9.0, fp 1.0->0.0, fn 6.0->12.0
- c36549w0004 (health_dense): topic tp 16.0->10.0, fp 5.0->0.0, fn 7.0->11.0
- c176579w0010 (rare_label): topic tp 8.0->15.0, fp 0.0->0.0, fn 15.0->8.0
- c182305w0009 (rare_label): topic tp 9.0->16.0, fp 0.0->2.0, fn 12.0->7.0
- c182604w0018 (narrative): topic tp 14.0->20.0, fp 2.0->1.0, fn 12.0->5.0
- c190127w0009 (narrative): topic tp 12.0->19.0, fp 0.0->0.0, fn 19.0->12.0
- c78775w0002 (narrative): topic tp 6.0->14.0, fp 0.0->0.0, fn 8.0->2.0
