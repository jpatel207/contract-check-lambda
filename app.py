import pandas as pd
import psycopg2
import os
import boto3
from io import StringIO
from datetime import timedelta
from simple_salesforce import Salesforce

def lambda_handler(event, context):
    s3_bucket = os.environ['CSV_BUCKET']
    output_key = os.environ['OUTPUT_KEY']
    s3 = boto3.client('s3')

    sf = Salesforce(
        username=os.environ['SF_USERNAME'],
        password=os.environ['SF_PASSWORD'],
        security_token=os.environ['SF_TOKEN']
    )

    soql_query = """
    SELECT 
        Id,
        LastModifiedDate,
        Contract__c,
        Event_Code__r.Name,
        Event_Code__r.Event_Type_Description__c,
        Event_Code__r.Inactive__c
    FROM Contract_Event__c
    """

    results = sf.query_all(soql_query)
    sf_records = results['records']
    sf_df = pd.DataFrame(sf_records).drop(columns=['attributes'])
    sf_df['LastModifiedDate'] = pd.to_datetime(sf_df['LastModifiedDate'], utc=True)

    warehouse_query = """
    SELECT contracteventid,
           deletedindicator,
           contracteventname,
           contractid,
           contracteventcode,
           contracteventcodedescription,
           CASE
               WHEN contracteventcodeactiveindicator IS FALSE THEN TRUE
               WHEN contracteventcodeactiveindicator IS TRUE THEN FALSE
           END AS eventcodeinactiveindicator,
           contracteventcomments,
           defaultstatuscode,
           eventdate,
           postexecutionaddendumreasoncodes,
           terminationreasoncode,
           contracteventlastupdatedatetimegmt
    FROM analytics_schema.contract_events_view
    WHERE deletedindicator = false
    """

    with psycopg2.connect(
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        host=os.environ['DB_HOST'],
        port=5439,
        sslmode='require'
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(warehouse_query)
            result = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            warehouse_df = pd.DataFrame(result, columns=column_names)

    warehouse_df['contracteventlastupdatedatetimegmt'] = pd.to_datetime(
        warehouse_df['contracteventlastupdatedatetimegmt'], utc=True
    )

    df = sf_df.merge(warehouse_df, how='outer', left_on='Id', right_on='contracteventid')
    five_hours_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=5)

    mismatch = df[
        (df['contracteventlastupdatedatetimegmt'] != df['LastModifiedDate']) &
        (df['LastModifiedDate'] < five_hours_ago)
    ]

    csv_buffer = StringIO()
    mismatch.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=s3_bucket, Key=output_key, Body=csv_buffer.getvalue())

    return {
        "statusCode": 200,
        "body": f"Mismatch file uploaded to s3://{s3_bucket}/{output_key}"
    }
