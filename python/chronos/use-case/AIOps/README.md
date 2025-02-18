## Anomaly detection use case in Chronos

---
We demonstrate how to use Chronos to detect anomaly data  based on historical time series data. And measure the distance between predicted values and actual values. If the distance is above some threshold, we report those values as anomaly.

In the reference use case, we use the publicly available cluster trace data cluster-trace-v2018 of Alibaba Open Cluster Trace Program. ([dataset link](http://clusterdata2018pubcn.oss-cn-beijing.aliyuncs.com/machine_usage.tar.gz)). 
 

This use case example contains two notebooks:

- **AIOps_anomaly_detect_unsupervised_forecast_based.ipynb** demonstrates how to leverage Chronos's built-in models ie. MTNet, to do time series forecasting. Then perform anomaly detection on predicted value with [ThresholdDetector](https://bigdl.readthedocs.io/en/latest/doc/PythonAPI/Chronos/anomaly_detectors.html#thresholddetector).

- **AIOps_anomaly_detect_unsupervised.ipynb** demonstrates how to perform anomaly detection based on Chronos's built-in [DBScanDetector](https://bigdl.readthedocs.io/en/latest/doc/PythonAPI/Chronos/anomaly_detectors.html#dbscandetector), [AEDetector](https://bigdl.readthedocs.io/en/latest/doc/PythonAPI/Chronos/anomaly_detectors.html#aedetector) and [ThresholdDetector](https://bigdl.readthedocs.io/en/latest/doc/PythonAPI/Chronos/anomaly_detectors.html#thresholddetector).

### Install

You can refer to Chronos installation document [here](https://bigdl.readthedocs.io/en/latest/doc/Chronos/Overview/install.html).

### Prepare dataset
* run `get_data.sh` to download the full dataset. It will download the resource usage of each machine from m_1932 to m_2085. 
* run `extract_data.sh` to extract records of machine 1932. The script will extract the m_1932 with timestamps into `m_1932.csv`.


