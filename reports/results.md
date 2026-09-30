# Backtest results

Headlines: 4388  |  threshold 0.3  |  round-trip cost 0.25%  |  risk-free 6.5%


## Hold 1 day(s), including price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|
| negative |   685.00 |            -0.00 |        47.30 |    -0.01 |
| neutral  |  1750.00 |             0.04 |        50.06 |     0.93 |
| positive |  1233.00 |            -0.11 |        45.74 |    -2.21 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |   -17.02 |    -1.52 |    -93.76 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    43.03 |     0.85 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |    -2.10 |    -1.02 |    -55.15 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.89 |     0.43 |    -37.55 |
| full period               | news long-only  |   -10.58 |    -1.31 |    -96.98 |
| full period               | buy & hold (EW) |    28.50 |     0.68 |    -56.92 |



## Hold 1 day(s), excluding price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|
| negative |   600.00 |            -0.01 |        47.67 |    -0.09 |
| neutral  |  1731.00 |             0.04 |        49.97 |     0.90 |
| positive |  1009.00 |            -0.06 |        46.98 |    -1.14 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |   -13.78 |    -1.41 |    -88.93 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    43.03 |     0.85 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |     0.28 |    -0.78 |    -44.50 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.89 |     0.43 |    -37.55 |
| full period               | news long-only  |    -7.67 |    -1.16 |    -93.54 |
| full period               | buy & hold (EW) |    28.50 |     0.68 |    -56.92 |



## Hold 5 day(s), including price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|
| negative |   685.00 |             0.10 |        51.09 |     0.69 |
| neutral  |  1750.00 |            -0.10 |        47.49 |    -1.07 |
| positive |  1233.00 |            -0.49 |        45.34 |    -4.52 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |   -15.47 |    -0.48 |    -94.69 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    43.03 |     0.85 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |     3.55 |    -0.20 |    -37.05 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.89 |     0.43 |    -37.55 |
| full period               | news long-only  |    -7.34 |    -0.38 |    -94.69 |
| full period               | buy & hold (EW) |    28.50 |     0.68 |    -56.92 |



## Hold 5 day(s), excluding price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|
| negative |   600.00 |             0.07 |        50.83 |     0.47 |
| neutral  |  1731.00 |            -0.12 |        47.54 |    -1.29 |
| positive |  1009.00 |            -0.41 |        45.69 |    -3.86 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |    -5.33 |    -0.40 |    -78.99 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    43.03 |     0.85 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |     6.24 |     0.02 |    -29.36 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.89 |     0.43 |    -37.55 |
| full period               | news long-only  |    -0.26 |    -0.26 |    -78.99 |
| full period               | buy & hold (EW) |    28.50 |     0.68 |    -56.92 |

