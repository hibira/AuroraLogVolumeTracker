# Author thibira@amazon.co.jp
# このコードは Aurora クラスタのログファイルの情報を、CloudWatch カスタムメトリクスに登録します。
# このコードに著作権は発生せず、自由にご利用頂けます。
# このコードはサンプルであり、動作を保証するものではありません。ご利用に際しては必ず検証を行なってください。

import boto3
import os
from datetime import datetime, timedelta


def lambda_handler(event, context):
    # 環境変数からインスタンス名を取得
    cluster_identifier = os.environ['AURORA_CLUSTER']
    print('AURORA_CLUSTER: ' + cluster_identifier)
    # ログディスクサイズの監視閾値を取得(Bytes)
    threshold_total_log_file_size = float(os.environ['THRESHOLD_TOTAL_LOG_FILE_SIZE'])
    print('THRESHOLD_TOTAL_LOG_FILE_SIZE(GB): ' + str(threshold_total_log_file_size))
    threshold_total_log_file_size = threshold_total_log_file_size * 1024 * 1024 * 1024
    # カスタムメトリクスの名前空間
    namespace = os.environ['METRICS_NAMESPACE']
    print('METRICS_NAMESPACE: ' + namespace)
    # ログファイルの合計サイズをカスタムメトリクスの情報を取得
    log_size_metrics_name = os.environ['TOTAL_LOG_FILE_SIZE_METRICS_NAME']
    print('TOTAL_LOG_FILE_SIZE_METRICS_NAME: ' + log_size_metrics_name)
    # 所定のローテーションが行われていないログファイル数をカスタムメトリクスの情報を取得
    threshold_metrics_name = os.environ['OVER_THRESHOLD_COUNT_METRICS_NAME']
    print('OVER_THRESHOLD_COUNT_METRICS_NAME: ' + threshold_metrics_name)

    rds = boto3.client('rds')
    cloudwatch = boto3.client('cloudwatch')

    response = rds.describe_db_instances(Filters=[{'Name': 'db-cluster-id', 'Values': [cluster_identifier]}])
    # インスタンスごとに走査
    for instance in response['DBInstances']:
        # ログファイルの情報を取得
        instance_identifier = instance['DBInstanceIdentifier']
        print('Instance Identifier: ' + instance_identifier)
        log_info = get_logfile_insight(rds, instance_identifier, threshold_total_log_file_size)

        # カスタムメトリクスの登録
        dimensions = [
            {'Name': 'DBClusterIdentifier', 'Value': cluster_identifier},
            {'Name': 'DBInstanceIdentifier', 'Value': instance_identifier}
        ]
        # ログファイルの合計サイズをカスタムメトリクスに登録
        add_metrics(cloudwatch, namespace, log_size_metrics_name, log_info['TotalLogSize'], 'Bytes', dimensions)
        # 所定のローテーションが行われていないログファイル数をカスタムメトリクスに登録
        add_metrics(cloudwatch, namespace, threshold_metrics_name, log_info['TotalOverCount'], 'Count', dimensions)

    return {
        'statusCode': 200,
        'body': 'Success'
    }


# インスタンスごとのログファイル情報を取得
def get_logfile_insight(rds_client, instance, threshold_total_log_file_size):
    total_size = 0
    log_files = []

    end_time = datetime.utcnow()
    # エラーログのローテーション期限。最長24時間で1時間ごとのローテーションされるため、25hを期限とする。
    before_1day_time = int((end_time - timedelta(hours=25)).timestamp() * 1000)
    # エラーログのローテーション期限。最長30日で1時間ごとのローテーションされるため、 24h*30day+1hを期限とする
    before_30day_time = int((end_time - timedelta(hours=24 * 30 + 1)).timestamp() * 1000)

    # 各ログファイルの情報を処理
    count = 0
    marker = ''
    over_audit_count = 0
    over_general_count = 0
    over_slowquery_count = 0
    over_error_count = 0
    while True:
        # ログファイルの一覧を取得
        response = rds_client.describe_db_log_files(
            DBInstanceIdentifier=instance,
            Marker=marker
        )
        for log_file in response['DescribeDBLogFiles']:
            file_name = log_file['LogFileName']
            file_size = log_file['Size']
            last_written = log_file['LastWritten']
            # print(file_name + " " + str(file_size) + "bytes " + str(last_written))
            log_files.append({
                'FileName': file_name,
                'Size': file_size,
                'LastWritten': last_written,
            })
            total_size += file_size
            if file_name.find('error/') >= 0 and before_30day_time > last_written:
                over_error_count = over_error_count + 1
                print('WARN: There are log files that have exceeded the rotation period !! - ' + file_name)
            if file_name.find('general/') >= 0 and before_1day_time > last_written:
                over_general_count = over_general_count + 1
                print('WARN: There are log files that have exceeded the rotation period !! - ' + file_name)
            if file_name.find('audit/') >= 0 and before_1day_time > last_written:
                over_audit_count = over_audit_count + 1
                print('WARN: There are log files that have exceeded the rotation period !! - ' + file_name)
            if file_name.find('slowquery/') >= 0 and before_1day_time > last_written:
                over_slowquery_count = over_slowquery_count + 1
                print('WARN: There are log files that have exceeded the rotation period !! - ' + file_name)
            count = count + 1

        if len(response['DescribeDBLogFiles']) < 1000:
            break
        marker = response['Marker']
        # print('Marker: ' + marker)

    print('INFO: over 30day error log count: ' + str(over_error_count))
    print('INFO: over 1day general log count: ' + str(over_general_count))
    print('INFO: over 1day audit log count: ' + str(over_audit_count))
    print('INFO: over 1day slowquery log count: ' + str(over_slowquery_count))
    print('INFO: total count: ' + str(count))
    print('INFO: total size (GB): ' + str(total_size / 1024 / 1024 / 1024))

    warn_file_count = over_error_count + over_general_count + over_audit_count + over_slowquery_count
    if threshold_total_log_file_size < total_size:
        print('WARN: Disk space threshold you specified has been exceeded!!')

    # 結果を返す
    return {
        'TotalLogSize': total_size,
        'LogFiles': log_files,
        'TotalCount': count,
        'TotalOverCount': warn_file_count,
        'OverErrorCount': over_error_count,
        'OverGeneralCount': over_general_count,
        'OverAuditCount': over_audit_count,
        'OverSlowqueryCount': over_slowquery_count,
    }


# カスタムメトリクスを登録
def add_metrics(cloudwatch, namespace, metrics_name, value, unit, dimensions):
    # CloudWatchにカスタムメトリクスを送信
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                'MetricName': metrics_name,
                'Value': value,
                'Unit': unit,
                'Dimensions': dimensions,
            },
        ]
    )
