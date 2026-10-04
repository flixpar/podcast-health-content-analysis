# Benchmark comparison: v7-high-b24k-r0 -> v7-refine

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-refine.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.728 | 0.782 | 0.054 | [0.041, 0.067] | 1.000 |
| topic recall (required) | 0.609 | 0.718 | 0.109 | [0.091, 0.128] | 1.000 |
| topic precision | 0.871 | 0.838 | -0.033 | [-0.044, -0.021] | 0.000 |
| narrative F1 (strict) | 0.776 | 0.813 | 0.037 | [0.011, 0.065] | 0.999 |
| frame F1 (strict) | 0.750 | 0.776 | 0.026 | [0.009, 0.045] | 0.999 |
| evidence F1 (strict) | 0.708 | 0.768 | 0.061 | [0.043, 0.079] | 1.000 |
| population F1 (strict) | 0.859 | 0.874 | 0.015 | [-0.014, 0.048] | 0.836 |
| claim recall (required) | 0.730 | 0.823 | 0.093 | [0.077, 0.108] | 1.000 |
| claim precision | 0.887 | 0.839 | -0.048 | [-0.059, -0.037] | 0.000 |
| product F1 (strict) | 0.880 | 0.879 | -0.000 | [-0.023, 0.021] | 0.498 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.695 | 0.765 | 0.703 | 0.769 |
| discourse | 0.708 | 0.750 | 0.751 | 0.836 |
| health_dense | 0.768 | 0.817 | 0.720 | 0.816 |
| mixed | 0.719 | 0.744 | 0.710 | 0.839 |
| narrative | 0.725 | 0.786 | 0.728 | 0.831 |
| null | 0.692 | 0.545 | 1.000 | 1.000 |
| rare_label | 0.709 | 0.769 | 0.722 | 0.810 |
| synthetic | 0.714 | 0.768 | 0.846 | 0.901 |

## Items that moved most (dev split)

- c28560w0006 (rare_label): topic tp 8.0->22.0, fp 0.0->1.0, fn 23.0->9.0
- c186894w0008 (narrative): topic tp 18.0->29.0, fp 0.0->6.0, fn 16.0->7.0
- c182721w0002 (health_dense): topic tp 32.0->40.0, fp 19.0->26.0, fn 21.0->13.0
- c182305w0009 (rare_label): topic tp 9.0->18.0, fp 0.0->3.0, fn 12.0->5.0
- c179765w0001 (health_dense): topic tp 24.0->33.0, fp 0.0->2.0, fn 14.0->7.0
- c5436w0023 (rare_label): topic tp 13.0->21.0, fp 1.0->2.0, fn 14.0->7.0
- c182604w0018 (narrative): topic tp 14.0->22.0, fp 2.0->2.0, fn 12.0->5.0
- c190127w0009 (narrative): topic tp 12.0->19.0, fp 0.0->0.0, fn 19.0->12.0
- c190550w0001 (health_dense): topic tp 12.0->19.0, fp 0.0->1.0, fn 9.0->3.0
- c174925w0002 (health_dense): topic tp 16.0->22.0, fp 6.0->4.0, fn 14.0->9.0
- c4171w0010 (rare_label): topic tp 6.0->0.0, fp 0.0->0.0, fn 0.0->6.0
- c78786w0019 (narrative): topic tp 12.0->18.0, fp 3.0->5.0, fn 6.0->2.0
- c176979w0018 (rare_label): topic tp 12.0->17.0, fp 3.0->4.0, fn 16.0->11.0
- c185744w0001 (rare_label): topic tp 9.0->13.0, fp 6.0->9.0, fn 8.0->4.0
- c193025w0004 (health_dense): topic tp 16.0->20.0, fp 2.0->5.0, fn 5.0->1.0
