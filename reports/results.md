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

| period                        | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:------------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)         | news long-only  |   -17.86 |    -1.53 |    -93.61 |
| 2001-2014 (in-sample)         | buy & hold (EW) |    32.41 |     0.98 |    -56.92 |
| 2015-mid 2020 (out-of-sample) | news long-only  |   -11.34 |    -1.49 |    -55.15 |
| 2015-mid 2020 (out-of-sample) | buy & hold (EW) |    13.24 |     0.41 |    -37.55 |
| full period                   | news long-only  |   -16.04 |    -1.51 |    -96.98 |
| full period                   | buy & hold (EW) |    26.60 |     0.85 |    -56.92 |



## Hold 1 day(s), excluding price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   600.00 |            -0.00 |        48.17 |    -0.01 |              -0.52 |        -2.94 |
| neutral  |  1719.00 |             0.04 |        50.38 |     0.96 |               0.18 |         1.74 |
| positive |  1003.00 |            -0.08 |        47.06 |    -1.37 |               0.41 |         3.09 |


Strategy vs benchmark:

| period                        | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:------------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)         | news long-only  |   -14.42 |    -1.41 |    -88.77 |
| 2001-2014 (in-sample)         | buy & hold (EW) |    32.41 |     0.98 |    -56.92 |
| 2015-mid 2020 (out-of-sample) | news long-only  |    -6.63 |    -1.14 |    -44.50 |
| 2015-mid 2020 (out-of-sample) | buy & hold (EW) |    13.24 |     0.41 |    -37.55 |
| full period                   | news long-only  |   -12.26 |    -1.34 |    -93.45 |
| full period                   | buy & hold (EW) |    26.60 |     0.85 |    -56.92 |



## Hold 5 day(s), including price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   685.00 |             0.10 |        50.95 |     0.69 |              -0.86 |        -4.92 |
| neutral  |  1738.00 |            -0.11 |        47.47 |    -1.16 |               0.22 |         2.19 |
| positive |  1227.00 |            -0.44 |        45.15 |    -4.47 |               0.50 |         4.19 |


Strategy vs benchmark:

| period                        | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:------------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)         | news long-only  |    -5.91 |    -0.39 |    -75.59 |
| 2001-2014 (in-sample)         | buy & hold (EW) |    32.41 |     0.98 |    -56.92 |
| 2015-mid 2020 (out-of-sample) | news long-only  |     0.06 |    -0.29 |    -37.05 |
| 2015-mid 2020 (out-of-sample) | buy & hold (EW) |    13.90 |     0.45 |    -37.55 |
| full period                   | news long-only  |    -4.23 |    -0.36 |    -75.59 |
| full period                   | buy & hold (EW) |    26.80 |     0.85 |    -56.92 |



## Hold 5 day(s), excluding price-report headlines

Event study (abnormal return vs equal-weight market):

| score    |   events |   mean_abn_ret_% |   hit_rate_% |   t_stat |   pre_5d_abn_ret_% |   pre_t_stat |
|:---------|---------:|-----------------:|-------------:|---------:|-------------------:|-------------:|
| negative |   600.00 |             0.07 |        50.67 |     0.48 |              -0.52 |        -2.94 |
| neutral  |  1719.00 |            -0.13 |        47.59 |    -1.37 |               0.18 |         1.74 |
| positive |  1003.00 |            -0.42 |        45.46 |    -3.91 |               0.41 |         3.09 |


Strategy vs benchmark:

| period                        | strategy        |   CAGR_% |   Sharpe |   MaxDD_% |
|:------------------------------|:----------------|---------:|---------:|----------:|
| 2001-2014 (in-sample)         | news long-only  |    -5.32 |    -0.39 |    -76.96 |
| 2001-2014 (in-sample)         | buy & hold (EW) |    32.41 |     0.98 |    -56.92 |
| 2015-mid 2020 (out-of-sample) | news long-only  |     5.70 |     0.03 |    -29.36 |
| 2015-mid 2020 (out-of-sample) | buy & hold (EW) |    13.90 |     0.45 |    -37.55 |
| full period                   | news long-only  |    -2.28 |    -0.29 |    -76.96 |
| full period                   | buy & hold (EW) |    26.80 |     0.85 |    -56.92 |

