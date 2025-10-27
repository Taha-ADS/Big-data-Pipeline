## End-to-End Big Data Analytics Pipeline for Amazon Review Sentiment Analysis

### **1. Objective**

The objective of this project was to design, implement, and deploy an end-to-end Big Data analytics pipeline. This system automates the ingestion, processing, analysis, and visualization of large-scale e-commerce review data, leveraging modern data engineering tools including Apache Spark, Apache Airflow, Google Cloud Platform (GCP), and Hugging Face AI models.

---

### **2. Pipeline Architecture & Technology Stack**

The pipeline was designed as a scalable, automated batch-processing system.

#### **2.1. Pipeline Flowchart (DAG)**
The logical flow of data is as follows:

Kaggle (Dataset) └──► Google Cloud Storage (Raw Data Lake) └──► Airflow / gsutil (Staging) └──► Apache Spark (Process & Analyze) └──► GCS (Processed Results) └──► Google BigQuery (Data Warehouse) └──► Looker Studio (Visualization)

<img width="480" height="480" alt="Gemini_Generated_Image_m0a8ebm0a8ebm0a8" src="https://github.com/user-attachments/assets/e3f07176-94c0-4670-9998-faae78fa5d2a" />


#### **2.2. Technology Stack**
* **Data Source:** Kaggle (Amazon Review Polarity Dataset)
* **Data Lake:** Google Cloud Storage (GCS)
* **Processing:** Apache Spark (PySpark)
* **AI/ML:** Hugging Face `transformers` (`distilbert-base-uncased-finetuned-sst-2-english`)
* **Data Warehouse:** Google BigQuery
* **Orchestration:** Apache Airflow (via Docker Compose)
* **Visualization:** Google Looker Studio

---

### **3. Implementation & Execution**

#### **Part A: Data Ingestion**
1.  **Dataset:** The **"Amazon Review Polarity"** dataset from Kaggle was selected. It contains 4,000,000 records (3,600,000 training, 400,000 test), easily meeting the "> 1 million records" requirement.
2.  **Loading:** The data was batch-loaded using Apache Spark.
3.  **Data Lake:** The raw `train.csv` and `test.csv` files were uploaded and stored in a Google Cloud Storage (GCS) bucket (`big-data-project-taha`), which serves as our central data lake.

#### **Part B: Data Processing & Transformation**
1.  **Cleaning:** A PySpark batch job was used to read the raw CSVs. This job performed the following transformations:
    * Combined the `train.csv` and `test.csv` files into a single DataFrame.
    * Dropped any rows with null values in the `text` or `polarity` columns.
    * Normalized the review text by converting it to lowercase.
    * Cleaned the text by using `regexp_replace` to remove all HTML tags (e.g., `<br>`) and special characters/punctuation.
2.  **Analytical Form:** The data was transformed into a clean, flat table (fact table) ready for AI analysis, containing the original `polarity`, `title`, and the new `text_clean` column.

#### **Part C: AI/ML Integration (Hugging Face)**
1.  **Model:** The pre-trained Hugging Face model **`distilbert-base-uncased-finetuned-sst-2-english`** was used for sentiment analysis.
2.  **Inference:** Model inference was integrated directly into the Spark pipeline using a **Pandas UDF (User-Defined Function)**. This allowed the AI model to be applied in a distributed manner across the Spark cluster, dramatically improving performance.
3.  **Storage:** The final DataFrame—containing the original polarity, the clean text, and the new AI-generated `sentiment_hf` label (POSITIVE/NEGATIVE)—was written as Parquet files and then loaded into a permanent Google BigQuery table: **`amazon_reviews.review_sentiments`**.

#### **Part D: Orchestration & Automation**
1.  **DAG Creation:** An **Apache Airflow DAG** (`big_data_assignment_pipeline`) was created to fully automate the end-to-end workflow. The DAG uses a single `BashOperator` to execute the entire sequence of tasks.
2.  **Workflow:**
    * **Task 1: Authenticate:** Activates the Google Cloud service account.
    * **Task 2: Ingest:** Copies raw data from GCS (`gsutil cp`) to the local Airflow worker for processing.
    * **Task 3: Process:** Executes the PySpark script (`python3 /tmp/run_spark.py`) to perform all cleaning and AI analysis, saving the results locally.
    * **Task 4: Upload:** Copies the processed Parquet files back to GCS (`gsutil cp`).
    * **Task 5: Load:** Uses the BigQuery CLI (`bq load`) to load the Parquet files from GCS into the final BigQuery table.
3.  **Automation:**
    * **Scheduling:** The DAG is scheduled to run daily using `schedule_interval="@daily"`.
    * **Resiliency:** The DAG is configured with `retries: 1` and a `retry_delay` of 5 minutes, ensuring it automatically retries once upon a temporary failure.
    * **Logging:** All logs from every step are automatically captured by Airflow and are viewable in the web UI for monitoring and debugging.

---

### **4. Part E: Visualization & Insights**

Here is a `README.md` section for your project's insights, formatted in clean, professional markdown. You can copy and paste this directly into your file.

-----

## 📊 Analysis & Insights

The pipeline processed a sample of 10,100 reviews, loading the results into BigQuery for analysis. The final data was visualized in Looker Studio, yielding three key insights.

### Insight 1: Sentiment Breakdown (57.5% Positive)

The primary analysis revealed a closely divided sentiment within the processed sample. The Hugging Face model classified **57.5% of the reviews as POSITIVE** and **42.5% as NEGATIVE**, indicating a mixed but slightly positive overall sentiment in the dataset.

### Insight 2: AI Model Accuracy (84.5%)

To validate the AI model, a confusion matrix was created comparing the dataset's original `polarity` label (1=Negative, 2=Positive) against the AI's predicted `sentiment_hf` label.

The results show a strong overall accuracy of **84.5%**:

  * The model correctly identified **4,690** reviews as negative (True Negatives).
  * The model correctly identified **3,840** reviews as positive (True Positives).

### Insight 3: Common Themes in Negative Feedback

By filtering the dashboard to isolate 'NEGATIVE' reviews, we identified clear, recurring themes in customer dissatisfaction. The most frequent titles for negative reviews were **"Disappointed"** (28 records), **"Disappointing"** (24 records), and **"Boring"** (13 records), strongly suggesting that a primary driver of negative feedback is the product failing to meet customer expectations.

---

### **5. Conclusion**

This project successfully demonstrates a robust, scalable, and fully automated Big Data pipeline. By integrating Apache Airflow for orchestration, Apache Spark for processing, and Hugging Face for advanced AI analysis, we were able to transform 4 million raw reviews from a data lake (GCS) into actionable insights in a data warehouse (BigQuery), which were then presented in a business-facing dashboard.
