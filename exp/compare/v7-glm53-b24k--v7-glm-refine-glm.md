# Benchmark comparison: v7-glm53-b24k -> v7-glm-refine-glm

Paired bootstrap over 303 item-repeat rows (303 shared items); positive delta favours v7-glm-refine-glm.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.733 | 0.791 | 0.058 | [0.045, 0.075] | 1.000 |
| topic recall (required) | 0.613 | 0.714 | 0.101 | [0.082, 0.123] | 1.000 |
| topic precision | 0.875 | 0.862 | -0.013 | [-0.024, -0.003] | 0.006 |
| narrative F1 (strict) | 0.751 | 0.802 | 0.051 | [0.019, 0.086] | 1.000 |
| frame F1 (strict) | 0.717 | 0.792 | 0.075 | [0.051, 0.101] | 1.000 |
| evidence F1 (strict) | 0.680 | 0.758 | 0.079 | [0.055, 0.104] | 1.000 |
| population F1 (strict) | 0.805 | 0.840 | 0.035 | [0.003, 0.069] | 0.985 |
| claim recall (required) | 0.684 | 0.780 | 0.096 | [0.079, 0.115] | 1.000 |
| claim precision | 0.923 | 0.897 | -0.026 | [-0.036, -0.016] | 0.000 |
| product F1 (strict) | 0.848 | 0.895 | 0.047 | [0.018, 0.082] | 0.999 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.741 | 0.786 | 0.736 | 0.813 |
| discourse | 0.764 | 0.804 | 0.676 | 0.770 |
| health_dense | 0.759 | 0.826 | 0.670 | 0.782 |
| mixed | 0.663 | 0.726 | 0.645 | 0.774 |
| narrative | 0.709 | 0.768 | 0.699 | 0.784 |
| null | 0.593 | 0.690 | 1.000 | 1.000 |
| rare_label | 0.734 | 0.794 | 0.667 | 0.763 |
| synthetic | 0.730 | 0.758 | 0.747 | 0.846 |

## Items that moved most (dev split)

- c174925w0002 (health_dense): topic tp 0.0->24.0, fp 0.0->3.0, fn 29.0->7.0
- c190562w0004 (health_dense): topic tp 0.0->18.0, fp 0.0->3.0, fn 21.0->3.0
- c175129w0004 (narrative): topic tp 0.0->12.0, fp 0.0->0.0, fn 13.0->3.0
- c182721w0002 (health_dense): topic tp 36.0->44.0, fp 8.0->10.0, fn 16.0->9.0
- c176556w0004 (narrative): topic tp 9.0->17.0, fp 0.0->0.0, fn 12.0->5.0
- c186894w0008 (narrative): topic tp 14.0->21.0, fp 4.0->3.0, fn 20.0->13.0
- c167665w0001 (narrative): topic tp 6.0->9.0, fp 8.0->4.0, fn 4.0->1.0
- c181355w0013 (rare_label): topic tp 0.0->5.0, fp 0.0->0.0, fn 13.0->9.0
- c95062w0004 (rare_label): topic tp 7.0->11.0, fp 0.0->1.0, fn 6.0->2.0
- c167673w0003 (narrative): topic tp 8.0->10.0, fp 3.0->7.0, fn 3.0->1.0
- c176604w0021 (rare_label): topic tp 13.0->17.0, fp 0.0->1.0, fn 5.0->2.0
- c177018w0009 (rare_label): topic tp 17.0->21.0, fp 1.0->2.0, fn 10.0->7.0
- c185864w0011 (rare_label): topic tp 3.0->7.0, fp 0.0->0.0, fn 5.0->2.0
- c193025w0004 (health_dense): topic tp 13.0->17.0, fp 3.0->3.0, fn 7.0->4.0
- c20037w0018 (narrative): topic tp 6.0->10.0, fp 5.0->5.0, fn 6.0->3.0
