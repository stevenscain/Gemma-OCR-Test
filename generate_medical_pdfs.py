"""Generate synthetic medical record PDFs using Faker for OCR testing."""

import os
import random
from datetime import timedelta
from faker import Faker
from fpdf import FPDF

fake = Faker()
OUTPUT_DIR = "test-pdfs"


def generate_patient_info():
    return {
        "name": fake.name(),
        "dob": fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y"),
        "ssn": fake.ssn(),
        "address": fake.address(),
        "phone": fake.phone_number(),
        "mrn": f"MRN-{fake.random_number(digits=8, fix_len=True)}",
        "insurance_id": f"INS-{fake.random_number(digits=10, fix_len=True)}",
    }


def generate_vitals():
    return {
        "blood_pressure": f"{random.randint(100, 160)}/{random.randint(60, 100)} mmHg",
        "heart_rate": f"{random.randint(55, 110)} bpm",
        "temperature": f"{round(random.uniform(97.0, 101.5), 1)}°F",
        "respiratory_rate": f"{random.randint(12, 24)} breaths/min",
        "oxygen_saturation": f"{random.randint(92, 100)}%",
        "weight": f"{random.randint(110, 280)} lbs",
        "height": f"{random.randint(58, 76)} in",
    }


DIAGNOSES = [
    "Essential Hypertension (I10)",
    "Type 2 Diabetes Mellitus (E11.9)",
    "Major Depressive Disorder, recurrent (F33.0)",
    "Acute Upper Respiratory Infection (J06.9)",
    "Chronic Obstructive Pulmonary Disease (J44.1)",
    "Gastroesophageal Reflux Disease (K21.0)",
    "Hyperlipidemia (E78.5)",
    "Osteoarthritis, unspecified (M19.90)",
    "Anxiety Disorder, unspecified (F41.9)",
    "Urinary Tract Infection (N39.0)",
    "Atrial Fibrillation (I48.91)",
    "Chronic Kidney Disease, Stage 3 (N18.3)",
]

MEDICATIONS = [
    ("Metformin", "500mg", "twice daily"),
    ("Lisinopril", "10mg", "once daily"),
    ("Atorvastatin", "20mg", "once daily at bedtime"),
    ("Metoprolol", "25mg", "twice daily"),
    ("Omeprazole", "20mg", "once daily before breakfast"),
    ("Sertraline", "50mg", "once daily"),
    ("Amlodipine", "5mg", "once daily"),
    ("Levothyroxine", "75mcg", "once daily on empty stomach"),
    ("Gabapentin", "300mg", "three times daily"),
    ("Hydrochlorothiazide", "25mg", "once daily"),
    ("Prednisone", "10mg", "taper over 7 days"),
    ("Amoxicillin", "500mg", "three times daily for 10 days"),
]

# ── Clinical narrative generators ─────────────────────────────────────────────

_HOSPITAL_COURSE_SENTENCES = [
    "Patient was admitted for acute management and close hemodynamic monitoring.",
    "On admission, the patient was alert and oriented, in mild-to-moderate distress.",
    "Initial assessment revealed tachycardia and elevated inflammatory markers.",
    "IV access was established and aggressive fluid resuscitation was initiated.",
    "The patient was placed on continuous telemetry and pulse oximetry.",
    "Cardiology was consulted and recommended rate control and anticoagulation therapy.",
    "Serial troponins were drawn and trended over the first 12 hours of admission.",
    "CT imaging of the chest and abdomen was obtained and reviewed with radiology.",
    "The patient was empirically started on broad-spectrum IV antibiotics pending culture results.",
    "Blood cultures, urine cultures, and respiratory cultures were obtained prior to antibiotic initiation.",
    "Nephrology was consulted for acute kidney injury with recommendations to hold nephrotoxic agents.",
    "The patient's electrolytes were repleted as needed with close monitoring of serum levels.",
    "Strict fluid balance was maintained with daily weight checks and accurate intake/output recording.",
    "Physical therapy and occupational therapy were consulted for early mobilization and functional assessment.",
    "The patient was maintained on a cardiac diet with a 2g sodium restriction.",
    "Insulin sliding scale was initiated for glycemic management with target glucose 140-180 mg/dL.",
    "Home medications were reviewed and held or adjusted as clinically indicated.",
    "The patient was transitioned from IV to oral antibiotics on hospital day three following clinical improvement.",
    "Repeat imaging demonstrated interval improvement with no new findings of concern.",
    "The patient remained afebrile and hemodynamically stable throughout the remainder of the hospitalization.",
    "Social work was involved to assist with discharge planning and community resource coordination.",
    "Respiratory therapy provided nebulization treatments every four hours with improvement in oxygen requirements.",
    "Vital signs trended toward baseline over the subsequent 48 hours.",
    "The patient demonstrated good understanding of the medication changes and dietary restrictions explained.",
    "By hospital day five, the patient met discharge criteria with stable vitals and tolerating oral intake.",
    "The patient was ambulating independently with supervision prior to discharge.",
    "Wound site was assessed daily with no signs of erythema, warmth, or purulent drainage.",
    "Echocardiogram demonstrated preserved ejection fraction with mild diastolic dysfunction.",
    "The patient's pain was adequately controlled with scheduled acetaminophen and PRN opioids.",
    "Case management coordinated a home health referral for post-discharge wound care and medication compliance.",
    "Pulmonology was consulted and recommended pulmonary function testing as an outpatient.",
    "DVT prophylaxis with subcutaneous heparin was maintained throughout the hospitalization.",
    "The patient was educated on fall prevention and instructed to use the call light as needed.",
    "Repeat laboratory values showed improvement in renal function and resolution of leukocytosis.",
    "Nutrition services were consulted for optimization of caloric intake and supplementation.",
    "The patient's family was present and actively involved in discharge planning discussions.",
]

_HOSPITAL_COURSE_OPENERS = [
    "Patient was admitted via the emergency department following {reason}.",
    "Patient presented with a {day}-day history of {symptom} and was admitted for further evaluation.",
    "Patient was transferred from an outside facility for higher level of care.",
    "Patient was admitted electively for management and optimization of chronic conditions.",
]

_HOSPITAL_COURSE_REASONS = [
    "acute decompensation of a known chronic condition",
    "new-onset chest pain with dyspnea",
    "fever, productive cough, and hypoxia",
    "acute onset confusion and altered mental status",
    "poorly controlled blood glucose and metabolic derangements",
    "hypertensive urgency with headache and visual changes",
    "abdominal pain with nausea and vomiting",
    "lower extremity swelling and exertional dyspnea",
]

_HOSPITAL_COURSE_DAYS = ["two", "three", "four", "five"]
_HOSPITAL_COURSE_SYMPTOMS = [
    "dyspnea and fatigue", "chest pain and palpitations", "fever and productive cough",
    "nausea, vomiting, and abdominal pain", "bilateral lower extremity edema",
]


def _hospital_course_paragraph() -> str:
    """Return one realistic hospital course narrative paragraph."""
    opener_tpl = random.choice(_HOSPITAL_COURSE_OPENERS)
    opener = opener_tpl.format(
        reason=random.choice(_HOSPITAL_COURSE_REASONS),
        day=random.randint(2, 7),
        symptom=random.choice(_HOSPITAL_COURSE_SYMPTOMS),
    )
    body = random.sample(_HOSPITAL_COURSE_SENTENCES, k=random.randint(4, 7))
    return opener + " " + " ".join(body)


# ── Consultation note narratives by specialty ──────────────────────────────────

_CONSULT_NOTES: dict[str, list[str]] = {
    "Cardiology": [
        "Patient evaluated for {indication}. Echocardiogram revealed preserved ejection fraction of {ef}% with mild diastolic dysfunction.",
        "Telemetry reviewed; rhythm consistent with {rhythm}. Rate control achieved with titration of beta-blockade.",
        "Recommend anticoagulation with apixaban given CHA2DS2-VASc score of {score}. Lipid panel reviewed; statin therapy optimized.",
        "Stress testing deferred given current clinical status; recommended as outpatient.",
        "Cardiac biomarkers trended downward over 12 hours, ruling out acute myocardial infarction by serial troponin protocol.",
        "Patient counseled on sodium restriction, daily weight monitoring, and signs of worsening heart failure.",
        "Follow-up in cardiology clinic in 2-4 weeks post-discharge with repeat echocardiogram at that visit.",
    ],
    "Pulmonology": [
        "Patient assessed for hypoxic respiratory failure requiring supplemental oxygen at {o2} L/min via nasal cannula.",
        "Chest X-ray reviewed demonstrating bilateral infiltrates consistent with the clinical picture.",
        "Recommend continuation of broad-spectrum antibiotics and reassessment in 48 hours.",
        "Pulmonary function testing recommended as outpatient once acute illness resolves.",
        "Inhaled bronchodilators and corticosteroids initiated with good subjective response.",
        "Oxygen weaned to {o2_d} L/min by day of discharge; patient instructed on home oxygen use.",
        "Smoking cessation counseling provided; nicotine replacement therapy initiated.",
        "Sleep study referral placed for suspected obstructive sleep apnea given clinical presentation and BMI.",
    ],
    "Infectious Disease": [
        "Patient evaluated for complicated infection requiring IV antibiotics.",
        "Culture sensitivities reviewed; antibiotic regimen narrowed to targeted coverage per susceptibilities.",
        "Recommend total antibiotic course of {days} days with transition to oral therapy once tolerating PO.",
        "Blood cultures finalized with no growth at 72 hours; IV antibiotics de-escalated accordingly.",
        "Source control assessed; no surgical intervention indicated at this time.",
        "Patient at risk for Clostridioides difficile; probiotics recommended and stool for C. diff sent.",
        "HIV and hepatitis serologies sent given clinical risk factors; results pending.",
        "Patient educated on medication adherence and signs and symptoms requiring return to care.",
    ],
    "Nephrology": [
        "Patient assessed for acute kidney injury, likely {etiology} in etiology.",
        "Nephrotoxic medications identified and held; IV fluid challenge administered with urine output monitored.",
        "Creatinine trending downward following fluid resuscitation and removal of offending agents.",
        "Renal ultrasound obtained to rule out obstructive uropathy; results without significant abnormality.",
        "Electrolytes closely monitored; potassium supplementation adjusted per daily levels.",
        "Patient educated on the importance of adequate hydration and avoidance of NSAIDs.",
        "Outpatient nephrology follow-up arranged with repeat metabolic panel in one week.",
        "Chronic kidney disease staging reviewed; dietary counseling with nephrology dietitian recommended.",
    ],
    "Endocrinology": [
        "Patient evaluated for suboptimal glycemic control with HbA1c elevated at {a1c}%.",
        "Insulin regimen reviewed and adjusted; basal-bolus strategy initiated with bedside glucose monitoring QID.",
        "Hypoglycemia protocol reviewed with nursing staff; glucagon kit ordered for the unit.",
        "Thyroid function tests obtained; results reviewed and levothyroxine dose adjusted.",
        "Patient and family counseled on carbohydrate counting, hypoglycemia recognition, and insulin administration technique.",
        "CGM initiation discussed with patient; referral placed for diabetes education program on discharge.",
        "Metformin held during hospitalization; to resume after discharge if renal function remains stable.",
        "A1c goal of <7% discussed with patient; medication compliance emphasized as key driver of glycemic control.",
    ],
}


def _consultation_note(specialty: str) -> str:
    """Return a realistic consultation note paragraph for the given specialty."""
    sentences = _CONSULT_NOTES.get(specialty, _CONSULT_NOTES["Cardiology"])
    chosen = random.sample(sentences, k=min(random.randint(4, 6), len(sentences)))
    filled = []
    for s in chosen:
        s = s.replace("{indication}", random.choice(["atrial fibrillation", "chest pain evaluation", "heart failure management"]))
        s = s.replace("{ef}", str(random.randint(45, 70)))
        s = s.replace("{rhythm}", random.choice(["atrial fibrillation with controlled ventricular rate", "normal sinus rhythm with occasional PVCs"]))
        s = s.replace("{score}", str(random.randint(2, 5)))
        s = s.replace("{o2}", str(random.randint(2, 6)))
        s = s.replace("{o2_d}", str(random.randint(1, 3)))
        s = s.replace("{days}", str(random.choice([7, 10, 14])))
        s = s.replace("{etiology}", random.choice(["prerenal", "intrinsic renal", "contrast-induced"]))
        s = s.replace("{a1c}", str(round(random.uniform(7.5, 11.5), 1)))
        filled.append(s)
    return " ".join(filled)


# ── Follow-up instruction sentences ───────────────────────────────────────────

_FOLLOWUP_SENTENCES = [
    "All new and changed medications have been reviewed in detail with the patient and caregiver.",
    "The patient verbalized understanding of the signs and symptoms requiring immediate return to the emergency department.",
    "Dietary counseling was reinforced with written materials provided in the patient's preferred language.",
    "A medication reconciliation list was provided at discharge and reviewed with the patient.",
    "The patient is instructed to weigh themselves daily and call the office if weight increases by more than 3 lbs in 24 hours.",
    "Home blood pressure monitoring is recommended with log to be brought to follow-up appointment.",
    "The patient should avoid strenuous physical activity until cleared at the follow-up appointment.",
    "All follow-up laboratory work has been pre-ordered and scheduled at the outpatient facility.",
    "Patient instructed to continue wound care as demonstrated by nursing staff prior to discharge.",
    "Emergency contact information and after-hours nurse line number provided to patient and family.",
]


def _followup_paragraph(doctor: str, follow_up_date_str: str) -> str:
    """Return realistic follow-up instruction text including the date and doctor."""
    sentences = random.sample(_FOLLOWUP_SENTENCES, k=random.randint(2, 4))
    return (
        f"Follow up with Dr. {doctor} on {follow_up_date_str}. "
        + " ".join(sentences)
    )


# ── Clinical interpretation paragraphs for lab reports ────────────────────────

_INTERP_SENTENCES = [
    "The complete blood count demonstrates a leukocytosis consistent with an acute infectious or inflammatory process.",
    "Hemoglobin is below the lower limit of normal, consistent with mild normocytic anemia; further workup including iron studies and reticulocyte count is recommended.",
    "The comprehensive metabolic panel reveals an elevated creatinine and BUN consistent with acute kidney injury; trending recommended.",
    "Liver function tests are within normal limits with no evidence of hepatocellular injury or cholestasis.",
    "Electrolyte panel reveals hyponatremia; fluid restriction and sodium supplementation should be considered.",
    "The lipid panel demonstrates elevated LDL cholesterol above goal; intensification of statin therapy is indicated.",
    "Hemoglobin A1c is above target, suggesting suboptimal glycemic control over the preceding 3 months.",
    "TSH is suppressed with elevated free T4, consistent with primary hyperthyroidism; endocrinology referral recommended.",
    "Platelet count is within normal limits; no thrombocytopenia or thrombocytosis identified.",
    "Fasting glucose is elevated above the normal threshold; correlation with clinical history and repeat testing recommended.",
    "Potassium is at the lower limit of normal; oral supplementation and repeat level in 1-2 days advised.",
    "Albumin is mildly decreased, suggesting possible nutritional deficiency or protein-losing process; clinical correlation advised.",
    "Triglycerides are significantly elevated; lifestyle modification including dietary fat restriction and increased aerobic activity recommended.",
    "The coagulation profile is within normal limits; no evidence of coagulopathy identified on this panel.",
    "Creatinine has trended downward compared to prior values, suggesting improvement in renal function with treatment.",
    "Elevated AST and ALT warrant hepatology consultation and investigation for underlying hepatic pathology.",
    "These results have been reviewed by the laboratory director and are consistent with the clinical diagnosis.",
    "Critical values, if any, were communicated directly to the ordering provider per laboratory policy.",
]


def _clinical_interpretation_paragraph() -> str:
    """Return one realistic clinical interpretation paragraph for a lab report."""
    sentences = random.sample(_INTERP_SENTENCES, k=random.randint(3, 5))
    return " ".join(sentences)


LAB_TESTS = [
    ("Glucose, Fasting", lambda: f"{random.randint(70, 250)} mg/dL", "70-100 mg/dL"),
    ("Hemoglobin A1c", lambda: f"{round(random.uniform(4.5, 12.0), 1)}%", "4.0-5.6%"),
    ("Total Cholesterol", lambda: f"{random.randint(140, 300)} mg/dL", "<200 mg/dL"),
    ("LDL Cholesterol", lambda: f"{random.randint(50, 200)} mg/dL", "<100 mg/dL"),
    ("HDL Cholesterol", lambda: f"{random.randint(25, 90)} mg/dL", ">40 mg/dL"),
    ("Triglycerides", lambda: f"{random.randint(50, 400)} mg/dL", "<150 mg/dL"),
    ("Creatinine", lambda: f"{round(random.uniform(0.5, 3.5), 2)} mg/dL", "0.7-1.3 mg/dL"),
    ("BUN", lambda: f"{random.randint(5, 45)} mg/dL", "7-20 mg/dL"),
    ("WBC", lambda: f"{round(random.uniform(3.0, 18.0), 1)} K/uL", "4.5-11.0 K/uL"),
    ("Hemoglobin", lambda: f"{round(random.uniform(8.0, 18.0), 1)} g/dL", "12.0-17.5 g/dL"),
    ("Platelet Count", lambda: f"{random.randint(100, 450)} K/uL", "150-400 K/uL"),
    ("TSH", lambda: f"{round(random.uniform(0.1, 10.0), 2)} mIU/L", "0.4-4.0 mIU/L"),
    ("Sodium", lambda: f"{random.randint(130, 150)} mEq/L", "136-145 mEq/L"),
    ("Potassium", lambda: f"{round(random.uniform(2.8, 6.0), 1)} mEq/L", "3.5-5.0 mEq/L"),
]


def add_header_footer(pdf, facility_name, facility_addr, facility_phone, facility_fax):
    """Add consistent header/footer to each page."""
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, facility_name, ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, facility_addr, ln=True, align="C")
    pdf.cell(0, 5, f"Phone: {facility_phone}  |  Fax: {facility_fax}", ln=True, align="C")
    pdf.line(10, pdf.get_y() + 3, 200, pdf.get_y() + 3)
    pdf.ln(8)


def make_discharge_summary(filepath, multipage=False):
    patient = generate_patient_info()
    vitals = generate_vitals()
    admit_date = fake.date_between(start_date="-60d", end_date="-2d")
    discharge_date = admit_date + timedelta(days=random.randint(1, 14))
    doctor = fake.name()
    diagnoses = random.sample(DIAGNOSES, k=random.randint(2, 5) if not multipage else random.randint(4, 6))
    meds = random.sample(MEDICATIONS, k=random.randint(3, 6) if not multipage else random.randint(6, 10))

    facility_name = fake.company() + " Medical Center"
    facility_addr = fake.address().replace("\n", ", ")
    facility_phone = fake.phone_number()
    facility_fax = fake.phone_number()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Header
    add_header_footer(pdf, facility_name, facility_addr, facility_phone, facility_fax)

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "DISCHARGE SUMMARY", ln=True, align="C")
    pdf.ln(5)

    # Patient Demographics
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "PATIENT INFORMATION", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, f"Patient Name: {patient['name']}")
    pdf.cell(0, 6, f"MRN: {patient['mrn']}", ln=True)
    pdf.cell(95, 6, f"Date of Birth: {patient['dob']}")
    pdf.cell(0, 6, f"Insurance ID: {patient['insurance_id']}", ln=True)
    pdf.cell(95, 6, f"Admission Date: {admit_date.strftime('%m/%d/%Y')}")
    pdf.cell(0, 6, f"Discharge Date: {discharge_date.strftime('%m/%d/%Y')}", ln=True)
    pdf.cell(0, 6, f"Attending Physician: Dr. {doctor}", ln=True)
    pdf.ln(5)

    # Vitals at Discharge
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "VITALS AT DISCHARGE", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, f"BP: {vitals['blood_pressure']}")
    pdf.cell(0, 6, f"HR: {vitals['heart_rate']}", ln=True)
    pdf.cell(95, 6, f"Temp: {vitals['temperature']}")
    pdf.cell(0, 6, f"SpO2: {vitals['oxygen_saturation']}", ln=True)
    pdf.cell(95, 6, f"Resp Rate: {vitals['respiratory_rate']}")
    pdf.cell(0, 6, f"Weight: {vitals['weight']}", ln=True)
    pdf.ln(5)

    # Diagnoses
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "DIAGNOSES", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for i, dx in enumerate(diagnoses, 1):
        pdf.cell(0, 6, f"  {i}. {dx}", ln=True)
    pdf.ln(5)

    # Hospital Course - longer for multipage
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "HOSPITAL COURSE", ln=True)
    pdf.set_font("Helvetica", "", 10)
    num_paragraphs = random.randint(4, 7) if multipage else 1
    for _ in range(num_paragraphs):
        pdf.multi_cell(0, 5, _hospital_course_paragraph())
        pdf.ln(3)
    pdf.ln(2)

    # Discharge Medications
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "DISCHARGE MEDICATIONS", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for i, (name, dose, freq) in enumerate(meds, 1):
        pdf.cell(0, 6, f"  {i}. {name} {dose} - {freq}", ln=True)
    pdf.ln(5)

    if multipage:
        # Additional sections to push to more pages
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "PROCEDURES PERFORMED", ln=True)
        pdf.set_font("Helvetica", "", 10)
        procedures = [
            "Central line placement (right internal jugular)",
            "CT scan of chest/abdomen/pelvis with IV contrast",
            "Echocardiogram (transthoracic)",
            "Bronchoscopy with lavage",
            "Blood transfusion (2 units packed RBCs)",
            "Lumbar puncture",
            "Arterial blood gas analysis",
        ]
        for i, proc in enumerate(random.sample(procedures, k=random.randint(3, 5)), 1):
            pdf.cell(0, 6, f"  {i}. {proc}", ln=True)
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "CONSULTATION NOTES", ln=True)
        pdf.set_font("Helvetica", "", 10)
        specialties = ["Cardiology", "Pulmonology", "Infectious Disease", "Nephrology", "Endocrinology"]
        for spec in random.sample(specialties, k=random.randint(2, 4)):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"  {spec} - Dr. {fake.name()}", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, f"    {_consultation_note(spec)}")
            pdf.ln(3)
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "PATIENT EDUCATION & DISCHARGE INSTRUCTIONS", ln=True)
        pdf.set_font("Helvetica", "", 10)
        instructions = [
            "Diet: Low sodium (<2g/day), diabetic diet as previously prescribed.",
            "Activity: No heavy lifting >10 lbs for 2 weeks. Gradual return to normal activity.",
            "Wound care: Keep incision site clean and dry. Change dressing daily.",
            "Warning signs: Return to ER if experiencing chest pain, shortness of breath, fever >101.5F, or worsening symptoms.",
            "Medications: Take all medications as prescribed. Do not skip doses.",
            f"Follow-up labs: CBC, CMP, and coagulation panel in 1 week at {fake.company()} Lab.",
            "Smoking cessation counseling provided. Patient advised to quit smoking.",
            f"Home health: {fake.company()} Home Health will contact within 48 hours for wound care visits.",
        ]
        for instruction in instructions:
            pdf.multi_cell(0, 5, f"  - {instruction}")
            pdf.ln(1)
        pdf.ln(5)

    # Follow-up
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "FOLLOW-UP INSTRUCTIONS", ln=True)
    pdf.set_font("Helvetica", "", 10)
    follow_up_date = discharge_date + timedelta(days=random.randint(7, 30))
    pdf.multi_cell(0, 5, _followup_paragraph(doctor, follow_up_date.strftime('%m/%d/%Y')))
    pdf.ln(8)

    # Signature
    pdf.cell(0, 6, f"Electronically signed by Dr. {doctor}", ln=True)
    pdf.cell(0, 6, f"Date: {discharge_date.strftime('%m/%d/%Y %I:%M %p')}", ln=True)

    pdf.output(filepath)
    return pdf.pages_count


def make_lab_report(filepath, multipage=False):
    patient = generate_patient_info()
    doctor = fake.name()
    facility_name = fake.company() + " Laboratory Services"
    facility_addr = fake.address().replace("\n", ", ")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Header
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, facility_name, ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, facility_addr, ln=True, align="C")
    pdf.line(10, pdf.get_y() + 3, 200, pdf.get_y() + 3)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "LABORATORY REPORT", ln=True, align="C")
    pdf.ln(5)

    # Patient info
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, f"Patient: {patient['name']}")
    pdf.cell(0, 6, f"MRN: {patient['mrn']}", ln=True)
    pdf.cell(95, 6, f"DOB: {patient['dob']}")

    # For multipage: generate multiple collection dates (panels over several days)
    num_panels = random.randint(3, 5) if multipage else 1
    collection_dates = []
    base_date = fake.date_between(start_date="-30d", end_date="-3d")
    for d in range(num_panels):
        collection_dates.append(base_date + timedelta(days=d))

    pdf.cell(0, 6, f"Collection Date: {collection_dates[0].strftime('%m/%d/%Y')}", ln=True)
    pdf.cell(95, 6, f"Ordering Physician: Dr. {doctor}")
    pdf.cell(0, 6, f"Report Date: {(collection_dates[-1] + timedelta(days=1)).strftime('%m/%d/%Y')}", ln=True)
    pdf.ln(8)

    def draw_lab_table(pdf, panel_name, labs, collection_date):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, f"{panel_name} - Collected {collection_date.strftime('%m/%d/%Y')}", ln=True)
        pdf.ln(2)

        # Lab table header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(60, 8, "Test", border=1, fill=True)
        pdf.cell(40, 8, "Result", border=1, fill=True)
        pdf.cell(45, 8, "Reference Range", border=1, fill=True)
        pdf.cell(30, 8, "Flag", border=1, fill=True, ln=True)

        # Lab rows
        pdf.set_font("Helvetica", "", 10)
        for test_name, value_fn, ref_range in labs:
            value = value_fn()
            flag = random.choice(["", "", "", "H", "L", "H", ""])
            pdf.cell(60, 7, test_name, border=1)
            pdf.cell(40, 7, value, border=1)
            pdf.cell(45, 7, ref_range, border=1)
            pdf.cell(30, 7, flag, border=1, ln=True)
        pdf.ln(5)

    if multipage:
        panels = [
            ("COMPLETE BLOOD COUNT (CBC)", [
                ("WBC", lambda: f"{round(random.uniform(3.0, 18.0), 1)} K/uL", "4.5-11.0 K/uL"),
                ("RBC", lambda: f"{round(random.uniform(3.5, 6.5), 2)} M/uL", "4.5-5.5 M/uL"),
                ("Hemoglobin", lambda: f"{round(random.uniform(8.0, 18.0), 1)} g/dL", "12.0-17.5 g/dL"),
                ("Hematocrit", lambda: f"{round(random.uniform(25.0, 55.0), 1)}%", "36-46%"),
                ("MCV", lambda: f"{round(random.uniform(70.0, 110.0), 1)} fL", "80-100 fL"),
                ("MCH", lambda: f"{round(random.uniform(25.0, 35.0), 1)} pg", "27-33 pg"),
                ("MCHC", lambda: f"{round(random.uniform(30.0, 38.0), 1)} g/dL", "32-36 g/dL"),
                ("Platelet Count", lambda: f"{random.randint(100, 450)} K/uL", "150-400 K/uL"),
                ("MPV", lambda: f"{round(random.uniform(7.0, 12.0), 1)} fL", "7.5-11.5 fL"),
            ]),
            ("COMPREHENSIVE METABOLIC PANEL (CMP)", [
                ("Glucose, Fasting", lambda: f"{random.randint(70, 250)} mg/dL", "70-100 mg/dL"),
                ("BUN", lambda: f"{random.randint(5, 45)} mg/dL", "7-20 mg/dL"),
                ("Creatinine", lambda: f"{round(random.uniform(0.5, 3.5), 2)} mg/dL", "0.7-1.3 mg/dL"),
                ("eGFR", lambda: f"{random.randint(15, 120)} mL/min", ">60 mL/min"),
                ("Sodium", lambda: f"{random.randint(130, 150)} mEq/L", "136-145 mEq/L"),
                ("Potassium", lambda: f"{round(random.uniform(2.8, 6.0), 1)} mEq/L", "3.5-5.0 mEq/L"),
                ("Chloride", lambda: f"{random.randint(95, 110)} mEq/L", "98-106 mEq/L"),
                ("CO2", lambda: f"{random.randint(18, 32)} mEq/L", "23-29 mEq/L"),
                ("Calcium", lambda: f"{round(random.uniform(7.5, 11.0), 1)} mg/dL", "8.5-10.5 mg/dL"),
                ("Total Protein", lambda: f"{round(random.uniform(5.0, 9.0), 1)} g/dL", "6.0-8.3 g/dL"),
                ("Albumin", lambda: f"{round(random.uniform(2.5, 5.5), 1)} g/dL", "3.5-5.5 g/dL"),
                ("Bilirubin, Total", lambda: f"{round(random.uniform(0.1, 3.0), 1)} mg/dL", "0.1-1.2 mg/dL"),
                ("ALP", lambda: f"{random.randint(30, 200)} U/L", "44-147 U/L"),
                ("AST", lambda: f"{random.randint(10, 150)} U/L", "10-40 U/L"),
                ("ALT", lambda: f"{random.randint(7, 150)} U/L", "7-56 U/L"),
            ]),
            ("LIPID PANEL", [
                ("Total Cholesterol", lambda: f"{random.randint(140, 300)} mg/dL", "<200 mg/dL"),
                ("LDL Cholesterol", lambda: f"{random.randint(50, 200)} mg/dL", "<100 mg/dL"),
                ("HDL Cholesterol", lambda: f"{random.randint(25, 90)} mg/dL", ">40 mg/dL"),
                ("Triglycerides", lambda: f"{random.randint(50, 400)} mg/dL", "<150 mg/dL"),
                ("VLDL Cholesterol", lambda: f"{random.randint(5, 60)} mg/dL", "5-40 mg/dL"),
            ]),
            ("THYROID PANEL", [
                ("TSH", lambda: f"{round(random.uniform(0.1, 10.0), 2)} mIU/L", "0.4-4.0 mIU/L"),
                ("Free T4", lambda: f"{round(random.uniform(0.5, 2.5), 2)} ng/dL", "0.8-1.8 ng/dL"),
                ("Free T3", lambda: f"{round(random.uniform(1.5, 5.0), 1)} pg/mL", "2.3-4.2 pg/mL"),
            ]),
            ("HEMOGLOBIN A1C", [
                ("Hemoglobin A1c", lambda: f"{round(random.uniform(4.5, 12.0), 1)}%", "4.0-5.6%"),
                ("Estimated Avg Glucose", lambda: f"{random.randint(70, 300)} mg/dL", "70-126 mg/dL"),
            ]),
        ]
        for i, (panel_name, panel_labs) in enumerate(panels[:num_panels]):
            draw_lab_table(pdf, panel_name, panel_labs, collection_dates[min(i, len(collection_dates)-1)])

        # Add clinical notes to push further
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "CLINICAL INTERPRETATION", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for _ in range(random.randint(2, 4)):
            pdf.multi_cell(0, 5, _clinical_interpretation_paragraph())
            pdf.ln(3)
    else:
        labs = random.sample(LAB_TESTS, k=random.randint(6, 12))
        draw_lab_table(pdf, "GENERAL PANEL", labs, collection_dates[0])

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "H = High, L = Low. Results outside reference range are flagged.", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Verified by: {fake.name()}, MD, Lab Director", ln=True)

    pdf.output(filepath)
    return pdf.pages_count


def make_prescription(filepath, multipage=False):
    patient = generate_patient_info()
    doctor = fake.name()
    med = random.choice(MEDICATIONS)
    rx_date = fake.date_between(start_date="-14d", end_date="today")

    pdf = FPDF()
    pdf.add_page()

    # Rx Header
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Dr. {doctor}", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    specialty = random.choice(["Internal Medicine", "Family Medicine", "Cardiology", "Endocrinology", "Pulmonology"])
    pdf.cell(0, 5, specialty, ln=True, align="C")
    pdf.cell(0, 5, fake.address().replace("\n", ", "), ln=True, align="C")
    pdf.cell(0, 5, f"Phone: {fake.phone_number()}  |  DEA#: {fake.bothify('??#######').upper()}", ln=True, align="C")
    pdf.cell(0, 5, f"NPI: {fake.random_number(digits=10, fix_len=True)}", ln=True, align="C")
    pdf.line(10, pdf.get_y() + 5, 200, pdf.get_y() + 5)
    pdf.ln(12)

    # Patient
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Date: {rx_date.strftime('%m/%d/%Y')}", ln=True)
    pdf.cell(0, 7, f"Patient Name: {patient['name']}", ln=True)
    pdf.cell(0, 7, f"DOB: {patient['dob']}    MRN: {patient['mrn']}", ln=True)
    pdf.cell(0, 7, f"Address: {patient['address'].replace(chr(10), ', ')}", ln=True)
    pdf.ln(10)

    # Rx symbol
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 12, "Rx", ln=True)
    pdf.ln(5)

    # Medication
    pdf.set_font("Helvetica", "", 13)
    name, dose, freq = med
    qty = random.choice([30, 60, 90])
    refills = random.randint(0, 5)
    pdf.cell(0, 8, f"{name} {dose}", ln=True)
    pdf.cell(0, 8, f"Sig: Take {freq}", ln=True)
    pdf.cell(0, 8, f"Qty: #{qty}    Refills: {refills}", ln=True)
    pdf.cell(0, 8, f"DAW: {random.choice(['Yes', 'No'])}", ln=True)
    pdf.ln(15)

    # Signature line
    pdf.line(10, pdf.get_y(), 100, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Prescriber Signature: Dr. {doctor}", ln=True)
    pdf.cell(0, 6, f"Date: {rx_date.strftime('%m/%d/%Y')}", ln=True)

    pdf.output(filepath)
    return pdf.pages_count


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Single-page documents
    generators = [
        ("discharge_summary", make_discharge_summary, 3, False),
        ("lab_report", make_lab_report, 3, False),
        ("prescription", make_prescription, 4, False),
    ]

    # Multi-page documents
    multipage_generators = [
        ("discharge_summary_multi", make_discharge_summary, 2, True),
        ("lab_report_multi", make_lab_report, 2, True),
    ]

    total = 0
    for doc_type, gen_fn, count, multipage in generators + multipage_generators:
        for i in range(1, count + 1):
            filename = f"{doc_type}_{i:02d}.pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)
            if multipage:
                pages = gen_fn(filepath, multipage=True)
            else:
                pages = gen_fn(filepath)
            print(f"Generated: {filepath} ({pages} page(s))")
            total += 1

    print(f"\nDone! Generated {total} synthetic medical PDFs in '{OUTPUT_DIR}/'")
