# Benchmark comparison: v7-union2 -> v7-refine

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-refine.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.773 | 0.782 | 0.009 | [-0.003, 0.022] | 0.924 |
| topic recall (required) | 0.703 | 0.718 | 0.015 | [-0.005, 0.036] | 0.926 |
| topic precision | 0.836 | 0.838 | 0.002 | [-0.011, 0.015] | 0.638 |
| narrative F1 (strict) | 0.795 | 0.813 | 0.018 | [-0.006, 0.042] | 0.928 |
| frame F1 (strict) | 0.784 | 0.776 | -0.008 | [-0.029, 0.013] | 0.212 |
| evidence F1 (strict) | 0.772 | 0.768 | -0.004 | [-0.020, 0.012] | 0.316 |
| population F1 (strict) | 0.882 | 0.874 | -0.007 | [-0.035, 0.022] | 0.304 |
| claim recall (required) | 0.801 | 0.823 | 0.022 | [0.007, 0.037] | 1.000 |
| claim precision | 0.851 | 0.839 | -0.012 | [-0.026, 0.001] | 0.045 |
| product F1 (strict) | 0.873 | 0.879 | 0.006 | [-0.020, 0.029] | 0.679 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.755 | 0.765 | 0.769 | 0.769 |
| discourse | 0.750 | 0.750 | 0.798 | 0.836 |
| health_dense | 0.805 | 0.817 | 0.776 | 0.816 |
| mixed | 0.785 | 0.744 | 0.806 | 0.839 |
| narrative | 0.773 | 0.786 | 0.810 | 0.831 |
| null | 0.688 | 0.545 | 1.000 | 1.000 |
| rare_label | 0.749 | 0.769 | 0.805 | 0.810 |
| synthetic | 0.796 | 0.768 | 0.868 | 0.901 |

## Items that moved most (dev split)

- c28560w0006 (rare_label): topic tp 9.0->22.0, fp 0.0->1.0, fn 22.0->9.0
- c182305w0009 (rare_label): topic tp 10.0->18.0, fp 2.0->3.0, fn 11.0->5.0
- c5436w0023 (rare_label): topic tp 14.0->21.0, fp 1.0->2.0, fn 14.0->7.0
- c176740w0013 (discourse): topic tp 14.0->9.0, fp 5.0->2.0, fn 6.0->11.0
- c192950w0011 (health_dense): topic tp 25.0->20.0, fp 3.0->0.0, fn 1.0->6.0
- c186894w0008 (narrative): topic tp 24.0->29.0, fp 3.0->6.0, fn 11.0->7.0
- c31510w0003 (narrative): topic tp 9.0->3.0, fp 2.0->2.0, fn 5.0->11.0
- c4171w0010 (rare_label): topic tp 6.0->0.0, fp 0.0->0.0, fn 0.0->6.0
- c193025w0004 (health_dense): topic tp 16.0->20.0, fp 2.0->5.0, fn 5.0->1.0
- c174925w0002 (health_dense): topic tp 18.0->22.0, fp 6.0->4.0, fn 13.0->9.0
- c176579w0010 (rare_label): topic tp 12.0->8.0, fp 0.0->1.0, fn 10.0->15.0
- c179765w0001 (health_dense): topic tp 28.0->33.0, fp 3.0->2.0, fn 11.0->7.0
- c185744w0001 (rare_label): topic tp 10.0->13.0, fp 6.0->9.0, fn 7.0->4.0
- c190235w0011 (rare_label): topic tp 5.0->8.0, fp 0.0->4.0, fn 3.0->1.0
- c190550w0001 (health_dense): topic tp 15.0->19.0, fp 2.0->1.0, fn 7.0->3.0
