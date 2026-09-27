from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup


#failure allert from context that gets the details of the crash when exitcode is not 0
def task_failure_alert(context):
    task_id = context.get('task_instance').task_id
    execution_date = context.get('execution_date')
    print(f" ALERT: Task '{task_id}' failed on execution date {execution_date}!")


# instaed of having args for each task, we have this default since no need to override for each one
default_args = {
    "owner": "data_engineering_team",
    "on_failure_callback": task_failure_alert,  # Triggers function on failure
    "depends_on_past": False,  # if a task fails, it doesnt affect the next one ( no blocking)
    "retries": 1,
}


with DAG(
    dag_id="social_media_analytics_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["production", "etl", "pyspark", "dbt"]
) as dag:

    #  Data Extraction 
    extract_task = BashOperator(
        task_id="phase1_data_extraction",
        bash_command="echo 'Starting extraction from raw JSON datasets...'"
    )

    #  PySpark Transformation & Loading Task
    spark_transform_load_task = BashOperator(
        task_id="phase2_and_3_pyspark_transform_and_load",
        bash_command="docker exec pyspark spark-submit --driver-class-path /home/jovyan/drivers/postgresql-42.7.3.jar /home/jovyan/work/etl_job.py"
    )

    # dbt Execution Task (Data Marts Build)
    with TaskGroup("phase4_dbt_data_marts_group") as dbt_task_group:
        
        dbt_run_marts = BashOperator(
            task_id="dbt_run_all_marts",
            bash_command="docker exec dbt dbt run"
        )
        dbt_test_marts = BashOperator(
            task_id="dbt_test_data_quality",
            bash_command="docker exec dbt dbt test"
        )
        dbt_run_marts >> dbt_test_marts

    # -------------------------------------------------------------
    # TASK DEPENDENCY FLOW 
    # -------------------------------------------------------------
    extract_task >> spark_transform_load_task >> dbt_task_group
