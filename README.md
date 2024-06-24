# AuroraLogVolumeTracker

Author thibira@amazon.co.jp  
このコードは Aurora クラスタのログファイルの情報を、CloudWatch カスタムメトリクスに登録します。  
このコードに著作権は発生せず、自由にご利用頂けます。  
このコードはサンプルであり、動作を保証するものではありません。ご利用に際しては必ず検証を行なってください。  

このコードを実行するには以下の環境変数が必要です。  
- AURORA_CLUSTER: 監査対象のクラスタを指定します。    
- THRESHOLD_TOTAL_LOG_FILE_SIZE: 例えば、500GB の 15% の場合は 「75」   
- METRICS_NAMESPACE: カスタムメトリクスの名前空間を指定してください (例) CUSTOM/RDS    
- TOTAL_LOG_FILE_SIZE_METRICS_NAME: ログファイルの合計サイズに関するメトリクス名 (例) TotalLogFileSize    
- OVER_THRESHOLD_COUNT_METRICS_NAME: ローテーション期限を超えて存在するログファイル数に関するメトリクス名 (例) OverThresholdCount   

また、以下のアクションに対する権限が必要です。
- rds:DescribeDBInstances
- rds:DescribeDbLogFiles
- cloudwatch:PutMetricData