from __future__ import annotations
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# ===================================================================
# 1. DEFINE YOUR GOOGLE CLOUD & PROJECT VARIABLES
# ===================================================================
PROJECT_ID = "project-cad8399d-08ce-4c7b-a33"  # !!! REPLACE WITH YOUR PROJECT ID
GCS_BUCKET_NAME = "big-data-project-taha"
BQ_DATASET = "amazon_reviews"
BQ_TABLE = "review_sentiments"
GCS_KEY_PATH = "/opt/airflow/dags/gcloud-key.json"

# This is the variable that was missing before
GCS_RESULTS_PATH = f"gs://{GCS_BUCKET_NAME}/results_data/" 

# ===================================================================
# 2. DEFINE THE SPARK PIPELINE SCRIPT
# ===================================================================
# This is our entire Spark/HuggingFace script from Colab
spark_pipeline_script = f"""
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim, lit
import pandas as pd
from transformers import pipeline
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType

print("Starting Spark session and downloading connectors...")

# 1. Initialize Spark Session
spark = SparkSession.builder \\
    .appName("AmazonReviewProcessing") \\
    .config("spark.jars.packages", "com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.23.2") \\
    .config("spark.hadoop.fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleFileSystem") \\
    .config("spark.hadoop.fs.AbstractFileSystem.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS") \\
    .getOrCreate()

print("Spark session created successfully.")

# 2. Define schema and paths
local_train_path = "/tmp/train.csv"
local_test_path = "/tmp/test.csv"
schema = StringType()
from pyspark.sql.types import StructType, StructField, IntegerType, StringType
schema = StructType([
    StructField("polarity", IntegerType(), True),
    StructField("title", StringType(), True),
    StructField("text", StringType(), True)
])

# 3. Read and Clean Data
print("Reading and processing local files...")
train_df = spark.read.option("header", "false").schema(schema).csv(local_train_path).withColumn("data_source", lit("train"))
test_df = spark.read.option("header", "false").schema(schema).csv(local_test_path).withColumn("data_source", lit("test"))
full_df = train_df.union(test_df)
clean_df = full_df \\
    .dropna(subset=["text", "polarity"]) \\
    .withColumn("text_clean", lower(col("text"))) \\
    .withColumn("text_clean", regexp_replace("text_clean", r"<[^>]+>", "")) \\
    .withColumn("text_clean", regexp_replace("text_clean", r"[^\\w\\s]", "")) \\
    .withColumn("text_clean", trim(col("text_clean"))) \\
    .filter(col("text_clean") != "")
print("Data cleaning complete.")

# 4. Define AI Model Function
def predict_sentiment(text_series: pd.Series) -> pd.Series:
    sentiment_pipeline = pipeline("sentiment-analysis", 
                                  model="distilbert-base-uncased-finetuned-sst-2-english", 
                                  device=-1)
    results = sentiment_pipeline(text_series.tolist(), truncation=True, max_length=512)
    return pd.Series([result['label'] for result in results])

sentiment_udf = pandas_udf(predict_sentiment, StringType())

# 5. Run AI Model
print("Starting Hugging Face sentiment analysis...")
sample_df = clean_df.limit(100)  # <-- !!! Run on 100 for testing. Change to 100000+ for final.
results_df = sample_df.withColumn("sentiment_hf", sentiment_udf(col("text_clean")))
print("Sentiment analysis complete.")

# 6. Save Results to Local Parquet
print("Saving results to local disk...")
local_results_path = "/tmp/results_parquet"
final_df = results_df.select(
    "polarity", "title", "text_clean", "sentiment_hf", "data_source"
)
final_df.write.format("parquet").mode("overwrite").save(local_results_path)

print("Local save complete. Spark job finished.")
"""

# ===================================================================
# 3. DEFINE THE DAG (Part D.1, D.2, D.3)
# ===================================================================
with DAG(
    dag_id="big_data_assignment_pipeline",
    start_date=datetime(2025, 10, 25),
    schedule_interval="@daily",  # Part D.2: Schedule to run daily
    catchup=False,
    default_args={
        "owner": "airflow",
        "retries": 1,  # Part D.3: Include retry mechanism
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False, 
        "email_on_retry": False,
    },
    tags=["big-data", "assignment", "spark", "huggingface"],
) as dag:

    # This task will run all our commands in a single, powerful bash script
    run_full_pipeline = BashOperator(
        task_id="run_full_pipeline",
        bash_command=f"""
            echo "================================================================="
            echo "STEP 1: Installing all dependencies..."
            pip install --quiet pyspark transformers torch pandas google-cloud-bigquery google-cloud-storage
            
            echo "================================================================="
            echo "STEP 2: Authenticating with Google Cloud..."
            gcloud auth activate-service-account --key-file={GCS_KEY_PATH}
            gcloud config set project {PROJECT_ID}
            
            echo "================================================================="
            echo "STEP 3 (Part A): Ingesting data from GCS Data Lake..."
            gsutil -m cp gs://{GCS_BUCKET_NAME}/train.csv /tmp/train.csv
            gsutil -m cp gs://{GCS_BUCKET_NAME}/test.csv /tmp/test.csv
            echo "File copying complete."
            
            echo "================================================================="
            echo "STEP 4 (Part B/C): Running Spark & AI Pipeline..."
            # Create the python script file
            echo "{spark_pipeline_script}" > /tmp/run_spark.py
            
            # Execute the python script
            python3 /tmp/run_spark.py
            echo "Spark job finished."

            echo "================================================================="
            echo "STEP 5 (Part C.3): Uploading results to GCS..."
            # We use the Python variable {GCS_RESULTS_PATH} defined at the top
            gsutil -m cp -r /tmp/results_parquet {GCS_RESULTS_PATH}
            echo "GCS upload complete."
            
            echo "================================================================="
            echo "STEP 6 (Part C.3): Loading data from GCS into BigQuery..."
            # We define the GCS URI for the bq command to use
            GCS_URI_FOR_BQ="{GCS_RESULTS_PATH}*.parquet"
            
            bq load \
                --source_format=PARQUET \
                --replace=true \
                "{PROJECT_ID}:{BQ_DATASET}.{BQ_TABLE}" \
                "$GCS_URI_FOR_BQ"
            echo "BigQuery load complete."

            echo "================================================================="
            echo "STEP 7: Cleaning up local files..."
            rm -rf /tmp/train.csv /tmp/test.csv /tmp/run_spark.py /tmp/results_parquet
            
            echo "PIPELINE COMPLETE! 🚀"
        """
    )