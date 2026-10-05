# Benchmark comparison: v7-refine -> v7-union-ds-glm

Paired bootstrap over 305 item-repeat rows (305 shared items); positive delta favours v7-union-ds-glm.

| metric | A | B | delta | 95% CI | P(B>A) |
| --- | --- | --- | --- | --- | --- |
| topic F1 (strict) | 0.782 | 0.784 | 0.002 | [-0.011, 0.014] | 0.596 |
| topic recall (required) | 0.718 | 0.709 | -0.008 | [-0.029, 0.010] | 0.196 |
| topic precision | 0.838 | 0.852 | 0.014 | [0.000, 0.028] | 0.978 |
| narrative F1 (strict) | 0.813 | 0.813 | -0.000 | [-0.029, 0.027] | 0.481 |
| frame F1 (strict) | 0.776 | 0.783 | 0.007 | [-0.013, 0.026] | 0.770 |
| evidence F1 (strict) | 0.768 | 0.773 | 0.005 | [-0.015, 0.023] | 0.686 |
| population F1 (strict) | 0.874 | 0.870 | -0.004 | [-0.037, 0.028] | 0.404 |
| claim recall (required) | 0.823 | 0.809 | -0.013 | [-0.029, 0.004] | 0.055 |
| claim precision | 0.839 | 0.857 | 0.018 | [0.005, 0.031] | 0.997 |
| product F1 (strict) | 0.879 | 0.858 | -0.021 | [-0.051, 0.009] | 0.081 |

## Per stratum delta (topic soft F1, claim recall)

| stratum | topic F1 A | topic F1 B | claim recall A | claim recall B |
| --- | --- | --- | --- | --- |
| ad_read | 0.765 | 0.797 | 0.769 | 0.846 |
| discourse | 0.750 | 0.784 | 0.836 | 0.775 |
| health_dense | 0.817 | 0.815 | 0.816 | 0.794 |
| mixed | 0.744 | 0.744 | 0.839 | 0.774 |
| narrative | 0.786 | 0.774 | 0.831 | 0.826 |
| null | 0.545 | 0.710 | 1.000 | 1.000 |
| rare_label | 0.769 | 0.774 | 0.810 | 0.803 |
| synthetic | 0.768 | 0.751 | 0.901 | 0.868 |

## Items that moved most (dev split)

- c186894w0008 (narrative): topic tp 29.0->21.0, fp 6.0->2.0, fn 7.0->13.0
- c176579w0010 (rare_label): topic tp 8.0->15.0, fp 1.0->0.0, fn 15.0->8.0
- c174925w0002 (health_dense): topic tp 22.0->16.0, fp 4.0->6.0, fn 9.0->14.0
- c176740w0013 (discourse): topic tp 9.0->15.0, fp 2.0->2.0, fn 11.0->5.0
- c182721w0002 (health_dense): topic tp 40.0->43.0, fp 26.0->20.0, fn 13.0->10.0
- c190550w0001 (health_dense): topic tp 19.0->13.0, fp 1.0->1.0, fn 3.0->9.0
- c4171w0010 (rare_label): topic tp 0.0->6.0, fp 0.0->0.0, fn 6.0->0.0
- c192950w0011 (health_dense): topic tp 20.0->25.0, fp 0.0->0.0, fn 6.0->1.0
- c5436w0023 (rare_label): topic tp 21.0->16.0, fp 2.0->1.0, fn 7.0->11.0
- c78786w0019 (narrative): topic tp 18.0->13.0, fp 5.0->4.0, fn 2.0->6.0
- c167665w0001 (narrative): topic tp 10.0->8.0, fp 2.0->7.0, fn 0.0->2.0
- c185744w0001 (rare_label): topic tp 13.0->10.0, fp 9.0->6.0, fn 4.0->7.0
- c193025w0004 (health_dense): topic tp 20.0->17.0, fp 5.0->2.0, fn 1.0->4.0
- c28560w0006 (rare_label): topic tp 22.0->26.0, fp 1.0->0.0, fn 9.0->5.0
- c178189w0009 (narrative): topic tp 16.0->19.0, fp 1.0->0.0, fn 11.0->7.0
