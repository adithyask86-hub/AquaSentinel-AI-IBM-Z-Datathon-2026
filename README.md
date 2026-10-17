# AquaSentinel AI
## Explainable Water-Quality Anomaly Screening and Decision Support

AquaSentinel AI is a data-driven prototype that screens historical water-conductivity measurements for unusual values and helps prioritise records for human review.

### Problem
Water-monitoring datasets can contain unusual measurements, missing values, and stations with insufficient historical observations. Reviewing every record manually can be inefficient.

### Solution
AquaSentinel AI combines:
- Station-specific robust statistical anomaly screening using the median and median absolute deviation (MAD).
- Data-quality checks for missing or invalid conductivity readings.
- Rule-based review prioritisation.
- A dashboard for searching stations, filtering review queues, and examining recommended actions.
- CSV exports for further analysis and audit.

### Current implementation
The prototype runs Python analysis scripts and a web dashboard on IBM LinuxONE Community Cloud.

### Dataset

Source: [India National Water Data Portal — CPCB Karnataka physical-parameter dataset](https://nwdp.nwic.gov.in/dataset/c547abaa-fbdc-4f46-b152-dc023be0c75c/resource/fc936b2d-a0ae-4d71-8bc6-ca95f99ee7dd/download/swq_physical_parameter_manual_cpcb_ka_2021_2025.csv)

The downloaded file contains observations from 2021, despite the year range in its filename. The analysis uses numeric conductivity readings where available. The original source records are retained; flagged values are not silently deleted or corrected.

Dataset size: 2,115 records, including 1,805 valid numeric conductivity readings from Karnataka.

### Demonstrated results
- Source records processed: 2,115
- Valid conductivity readings: 1,805
- Missing or invalid readings: 310
- Candidate anomalies: 65
- Records with insufficient station history: 87

These are exploratory screening results, not verified pollution detections or model-accuracy measurements.

### Method
For stations with sufficient historical observations, the system compares conductivity values with station-specific robust statistics. A rule-based layer assigns review priorities and recommended actions. Missing data and insufficient evidence are tracked separately.

The 5,000 µS/cm threshold is exploratory and is not a regulatory water-quality limit.

### Outputs
- `outputs/station_anomaly_review.csv`
- `outputs/analysis_summary.json`
- `outputs/decision_support_queue.csv`
- `outputs/linear_forecast_evaluation.csv`

### Run the prototype
Activate the project environment and run:

```bash
source .venv/bin/activate
python src/analyze.py
python src/decision_support.py
python src/dashboard.py
