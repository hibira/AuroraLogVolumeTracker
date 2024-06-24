# Author thibira@amazon.co.jp
# ローカルで実行する場合のサンプルコードです。

import os
import app

os.environ['AURORA_CLUSTER'] = 'aws-rails-sample'
os.environ['THRESHOLD_TOTAL_LOG_FILE_SIZE'] = str(0.001 * 0.15)
os.environ['METRICS_NAMESPACE'] = 'CUSTOM/RDS'
os.environ['TOTAL_LOG_FILE_SIZE_METRICS_NAME'] = 'TotalLogFileSize'
os.environ['OVER_THRESHOLD_COUNT_METRICS_NAME'] = 'OverThresholdCount'

app.lambda_handler("", "")
