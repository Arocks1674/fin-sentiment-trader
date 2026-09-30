# Backtest results

Headlines: 4388  |  threshold 0.3  |  round-trip cost 0.25%  |  risk-free 6.5%

Price rows removed by cleaning: 1024 (before_listing: 531, zero_volume: 492, bad_tick: 1)


## Hold 1 day(s), including price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   685.00 |             0.00 |        47.74 |     0.06 |              -0.86 |        -4.92 |
| neutral  |  1738.00 |             0.04 |        50.40 |     0.98 |               0.22 |         2.19 |
| positive |  1227.00 |            -0.13 |        45.88 |    -2.42 |               0.50 |         4.19 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |   -17.25 |    -1.51 |    -93.61 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    30.77 |     0.93 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |    -2.12 |    -1.02 |    -55.15 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.66 |     0.41 |    -37.55 |
| full period               | news long-only  |   -10.67 |    -1.30 |    -96.98 |
| full period               | buy & hold (EW) |    22.18 |     0.73 |    -56.92 |



## Hold 1 day(s), excluding price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   600.00 |            -0.00 |        48.17 |    -0.01 |              -0.52 |        -2.94 |
| neutral  |  1719.00 |             0.04 |        50.38 |     0.96 |               0.18 |         1.74 |
| positive |  1003.00 |            -0.08 |        47.06 |    -1.37 |               0.41 |         3.09 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |   -13.89 |    -1.39 |    -88.77 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    30.77 |     0.93 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |     0.27 |    -0.78 |    -44.50 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.66 |     0.41 |    -37.55 |
| full period               | news long-only  |    -7.70 |    -1.15 |    -93.45 |
| full period               | buy & hold (EW) |    22.18 |     0.73 |    -56.92 |



## Hold 5 day(s), including price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   685.00 |             0.10 |        50.95 |     0.69 |              -0.86 |        -4.92 |
| neutral  |  1738.00 |            -0.11 |        47.47 |    -1.16 |               0.22 |         2.19 |
| positive |  1227.00 |            -0.44 |        45.15 |    -4.47 |               0.50 |         4.19 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |    -5.58 |    -0.38 |    -75.59 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    30.77 |     0.93 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |     3.55 |    -0.20 |    -37.05 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.66 |     0.41 |    -37.55 |
| full period               | news long-only  |    -1.52 |    -0.31 |    -75.59 |
| full period               | buy & hold (EW) |    22.18 |     0.73 |    -56.92 |



## Hold 5 day(s), excluding price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   600.00 |             0.07 |        50.67 |     0.48 |              -0.52 |        -2.94 |
| neutral  |  1719.00 |            -0.13 |        47.59 |    -1.37 |               0.18 |         1.74 |
| positive |  1003.00 |            -0.42 |        45.46 |    -3.91 |               0.41 |         3.09 |


Strategy vs benchmark:

| period                    | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:--------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)     | news long-only  |    -5.00 |    -0.38 |    -76.96 |
| 2001-2014 (in-sample)     | buy & hold (EW) |    30.77 |     0.93 |    -56.92 |
| 2015-2020 (out-of-sample) | news long-only  |     6.24 |     0.02 |    -29.36 |
| 2015-2020 (out-of-sample) | buy & hold (EW) |    12.66 |     0.41 |    -37.55 |
| full period               | news long-only  |    -0.03 |    -0.25 |    -76.96 |
| full period               | buy & hold (EW) |    22.18 |     0.73 |    -56.92 |

