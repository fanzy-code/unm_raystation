"""
Create and export ArcCheck QA for the last verification plan.
"""

from create_qa import CreatePatientQA
from export_qa_dicom import ExportPatientQA

if __name__ == "__main__":
    create_patient_instance = CreatePatientQA()
    create_patient_instance.create_qa_plan()
    export_patient_instance = ExportPatientQA()
    export_patient_instance.export_qa_plan(verification_plan_setting="last")
