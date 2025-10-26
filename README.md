# Big-data-Pipeline
%% This code creates a top-to-bottom flowchart for your pipeline
graph TD
    A[Kaggle (Dataset)] --> B[GCS (Raw Data Lake)];
    B --> C(gsutil cp (Staging));
    C --> D[Colab Local Disk];
    D --> E(Spark: Read & Clean);
    E --> F(Spark: Hugging Face Model);
    F --> G(Spark: Write Local Parquet);
    G --> H(gsutil cp (Upload to GCS));
    H --> I(bq load (Load to Warehouse));
    I --> J[BigQuery (Data Warehouse)];
    J --> K[Looker Studio (Visualization)];
