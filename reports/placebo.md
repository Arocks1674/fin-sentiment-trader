# Placebo: permutation test of the positive-minus-negative spread

Scores shuffled across events 2,000 times. Threshold 0.3.

`all_news_*` = mean abnormal return over every news day, whatever its tone.


## Hold 1 day(s), including price-report headlines

| window        |   pos_minus_neg_% |   placebo_2.5% |   placebo_97.5% |   p_value |   all_news_mean_% |   all_news_t |
|:--------------|------------------:|---------------:|----------------:|----------:|------------------:|-------------:|
| 5 days before |             1.356 |         -0.401 |           0.407 |     0.000 |             0.113 |        1.589 |
| after entry   |            -0.130 |         -0.171 |           0.165 |     0.129 |            -0.021 |       -0.707 |



## Hold 1 day(s), excluding price-report headlines

| window        |   pos_minus_neg_% |   placebo_2.5% |   placebo_97.5% |   p_value |   all_news_mean_% |   all_news_t |
|:--------------|------------------:|---------------:|----------------:|----------:|------------------:|-------------:|
| 5 days before |             0.933 |         -0.418 |           0.416 |     0.000 |             0.121 |        1.638 |
| after entry   |            -0.077 |         -0.189 |           0.176 |     0.394 |            -0.002 |       -0.069 |



## Hold 5 day(s), including price-report headlines

| window        |   pos_minus_neg_% |   placebo_2.5% |   placebo_97.5% |   p_value |   all_news_mean_% |   all_news_t |
|:--------------|------------------:|---------------:|----------------:|----------:|------------------:|-------------:|
| 5 days before |             1.356 |         -0.401 |           0.407 |     0.000 |             0.113 |        1.589 |
| after entry   |            -0.538 |         -0.335 |           0.341 |     0.003 |            -0.181 |       -2.915 |



## Hold 5 day(s), excluding price-report headlines

| window        |   pos_minus_neg_% |   placebo_2.5% |   placebo_97.5% |   p_value |   all_news_mean_% |   all_news_t |
|:--------------|------------------:|---------------:|----------------:|----------:|------------------:|-------------:|
| 5 days before |             0.933 |         -0.418 |           0.416 |     0.000 |             0.121 |        1.638 |
| after entry   |            -0.488 |         -0.363 |           0.386 |     0.013 |            -0.180 |       -2.777 |

