"""
Extract HSE quarterly hospital cancellations from the PQ 1907/25 PDF.

Source: 'Hospital Cancellations 2002 to 2024 277,000 in 2024 pq-1907-25-cian-o-callaghan.pdf'
Output: supplementary data/cancellations_quarterly_by_hospital.csv

Output columns: HospitalGroup, Hospital, Region, Year, Quarter, Cancellations
- One row per (Hospital, Year, Quarter)
- Cancellations is the hospital total across all appointment types

Validation steps (raise on failure):
1. Hospital total row == sum of its appointment-type sub-rows
2. Group total row == sum of its hospital rows
3. National total per quarter (from PDF page 7) == sum of group totals

PDF caveat: 2022 reporting was incomplete — kept here for completeness; downstream
scaling scripts drop 2022.
"""

from pathlib import Path
import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
SUPP = ROOT / 'supplementary data'
PDF_PATH = SUPP / 'Hospital Cancellations 2002 to 2024 277,000 in 2024 pq-1907-25-cian-o-callaghan.pdf'
BEDS_PATH = SUPP / '2025_hr_beds_per_hospital.csv'
OUT_PATH = SUPP / 'cancellations_quarterly_by_hospital.csv'

GROUPS = {
    "Children's Health Ireland",
    'Dublin Midlands Hospital Group',
    'Ireland East Hospital Group',
    'RCSI Hospitals Group',
    'Saolta University Health Care Group',
    'South / South West Hospital Group',
    'UL Hospitals Group',
}

# PDF hospital name → beds CSV hospital name (only where they differ)
HOSPITAL_NAME_MAP = {
    "Children's Health Ireland": "Children's Health Ireland",
}

NATIONAL_TOTALS = {
    (2022, 1): 29247, (2022, 2): 45634, (2022, 3): 57556, (2022, 4): 56107,
    (2023, 1): 67329, (2023, 2): 61350, (2023, 3): 62901, (2023, 4): 65621,
    (2024, 1): 69449, (2024, 2): 71657, (2024, 3): 74036, (2024, 4): 61855,
}

QUARTER_COLUMNS = [(y, q) for y in (2022, 2023, 2024) for q in (1, 2, 3, 4)]


def _to_int(s: str) -> int:
    if s is None or s == '' or s.strip() == '':
        return 0
    return int(s.replace(',', '').strip())


def _row_values(row: list[str]) -> list[int]:
    return [_to_int(x) for x in row[1:13]]


def extract() -> pd.DataFrame:
    hospitals = pd.read_csv(BEDS_PATH)
    known_hospitals = set(hospitals['hospital'])

    rows = []
    current_group = None
    current_hospital = None
    hospital_totals = {}      # (hospital, year, qtr) -> reported total
    apptype_sums = {}         # (hospital, year, qtr) -> sum of appt-type rows
    group_totals = {}         # (group, year, qtr) -> reported total
    group_members = {}        # group -> set of hospitals seen

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages[2:7]:
            tables = page.extract_tables()
            for table in tables:
                for raw in table:
                    if not raw or not raw[0]:
                        continue
                    name = raw[0].strip()
                    if not name or name in {'Hospital Groups / Hospitals', '2022', '2023', '2024'}:
                        continue
                    if name.startswith('Qtr') or name.startswith('National Totals'):
                        if name.startswith('National Totals'):
                            for (y, q), v in zip(QUARTER_COLUMNS, _row_values(raw)):
                                expected = NATIONAL_TOTALS[(y, q)]
                                if v != expected:
                                    raise ValueError(
                                        f'National total mismatch {y}Q{q}: parsed {v}, expected {expected}'
                                    )
                        continue

                    values = _row_values(raw)

                    if name in GROUPS:
                        current_group = name
                        group_members.setdefault(name, set())
                        for (y, q), v in zip(QUARTER_COLUMNS, values):
                            group_totals[(name, y, q)] = v
                        # CHI's hospital row is the group row itself — handled below
                        if name == "Children's Health Ireland":
                            current_hospital = name
                            group_members[name].add(name)
                            for (y, q), v in zip(QUARTER_COLUMNS, values):
                                hospital_totals[(name, y, q)] = v
                                apptype_sums[(name, y, q)] = 0
                                rows.append({
                                    'HospitalGroup': current_group,
                                    'Hospital': name,
                                    'Year': y, 'Quarter': q, 'Cancellations': v,
                                })
                        continue

                    if name in known_hospitals:
                        current_hospital = name
                        group_members[current_group].add(name)
                        for (y, q), v in zip(QUARTER_COLUMNS, values):
                            hospital_totals[(name, y, q)] = v
                            apptype_sums[(name, y, q)] = 0
                            rows.append({
                                'HospitalGroup': current_group,
                                'Hospital': name,
                                'Year': y, 'Quarter': q, 'Cancellations': v,
                            })
                        continue

                    # Appointment-type sub-row — accumulate
                    if current_hospital is not None:
                        for (y, q), v in zip(QUARTER_COLUMNS, values):
                            apptype_sums[(current_hospital, y, q)] += v

    # --- Validations ---
    # 1) hospital totals == sum of appointment-type rows (for hospitals that have sub-rows)
    bad = []
    for k, total in hospital_totals.items():
        s = apptype_sums.get(k, 0)
        if s == 0:        # hospital with no sub-rows in that quarter; skip
            continue
        if s != total:
            bad.append((k, total, s))
    if bad:
        for k, total, s in bad[:10]:
            print(f'  hospital subtotal mismatch {k}: total={total}, sum_of_types={s}')
        raise ValueError(f'{len(bad)} hospital subtotal mismatches')

    # 2) group totals == sum of hospitals
    bad = []
    for group, members in group_members.items():
        for y, q in QUARTER_COLUMNS:
            reported = group_totals[(group, y, q)]
            summed = sum(hospital_totals.get((h, y, q), 0) for h in members)
            if reported != summed:
                bad.append((group, y, q, reported, summed))
    if bad:
        for b in bad[:10]:
            print(f'  group mismatch {b}')
        raise ValueError(f'{len(bad)} group total mismatches')

    # 3) national totals == sum of group totals
    for y, q in QUARTER_COLUMNS:
        s = sum(group_totals[(g, y, q)] for g in GROUPS)
        expected = NATIONAL_TOTALS[(y, q)]
        if s != expected:
            raise ValueError(f'National {y}Q{q}: sum of groups={s}, expected={expected}')

    df = pd.DataFrame(rows)

    # --- Region mapping ---
    region_map = hospitals.set_index('hospital')['region'].to_dict()
    df['Region'] = df['Hospital'].map(region_map)
    missing = df[df['Region'].isna()]['Hospital'].unique()
    if len(missing):
        raise ValueError(f'Hospitals without region mapping: {sorted(missing)}')

    df = df[['HospitalGroup', 'Hospital', 'Region', 'Year', 'Quarter', 'Cancellations']]
    df = df.sort_values(['Region', 'Hospital', 'Year', 'Quarter']).reset_index(drop=True)
    return df


if __name__ == '__main__':
    df = extract()
    df.to_csv(OUT_PATH, index=False)
    print(f'Validations passed.')
    print(f'Written: {OUT_PATH}')
    print(f'Rows: {len(df):,}  hospitals: {df["Hospital"].nunique()}  regions: {df["Region"].nunique()}')
    print()
    print('Per-region quarterly totals (2024):')
    pivot = (
        df[df['Year'] == 2024]
        .groupby(['Region', 'Quarter'])['Cancellations'].sum()
        .unstack('Quarter')
    )
    print(pivot.to_string())
