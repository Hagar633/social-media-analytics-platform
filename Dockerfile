FROM python:3.11.7-slim
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         git \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY installed-packages.txt ./installed-packages.txt
RUN  pip install --no-cache-dir -r ./installed-packages.txt
WORKDIR /app
COPY ./dbt_profiles/ /app/dbt_profiles/

RUN update-ca-certificates --verbose \
    && mkdir /root/.dbt \
    && ls && pwd \
    && cp ./dbt_profiles/* /root/.dbt/

ENTRYPOINT ["bash"]

