"""
Script to generate standard, valid RBIC Commercial Loan Compliance Policy PDF and Text documents.
"""
import os
import sys
from pathlib import Path
import pypdf

def build_pdf(filepath: Path):
    pages = [
        # PAGE 1
        [
            ("RESERVE BANK & FINANCIAL INSTITUTIONS COMPLIANCE MANUAL", 16, True, 740),
            ("COMMERCIAL LOAN COMPLIANCE CHECKING POLICY & PRUDENTIAL NORMS", 12, True, 715),
            ("Document Ref: RBIC/PRUD/2026-CR-08 | Applicable to Commercial & Corporate Lending", 9, False, 695),
            ("____________________________________________________________________________________________", 9, False, 685),
            ("SECTION 1: BORROWER STATUTORY ELIGIBILITY & CRILC VERIFICATION", 12, True, 660),
            ("1.1 Legal Entity Identifier (LEI) Mandate:", 10, True, 640),
            ("All corporate borrowers with aggregate credit exposure of INR 50 Crores ($10M) and above from the", 9, False, 625),
            ("banking system must obtain and maintain an active LEI code prior to sanction or renewal of facilities.", 9, False, 612),
            ("1.2 CRILC (Central Repository of Information on Large Credits) Verification:", 10, True, 592),
            ("Mandatory pre-sanction screening of CRILC database for exposures of INR 5 Crores and above to verify total", 9, False, 577),
            ("banking exposure, SMA status across member banks, and non-performing debt history.", 9, False, 564),
            ("1.3 Willful Defaulters & Non-Cooperative Borrowers:", 10, True, 544),
            ("Zero credit exposure is permitted to entities or directors appearing on RBI/CIBIL willful defaulters or", 9, False, 529),
            ("suit-filed lists. No compromise or restructuring without Special High-Powered Board Committee clearance.", 9, False, 516),
            ("1.4 KYC, AML & Ultimate Beneficial Ownership (UBO):", 10, True, 496),
            ("Mandatory verification of Ultimate Beneficial Owners holding 10% or more controlling interest or shareholding.", 9, False, 481),
            ("Annual AML screening against UN sanctions and domestic financial intelligence watchlists.", 9, False, 468),
            ("1.5 Statutory Credit Restrictions (Banking Regulation Act Section 20):", 10, True, 448),
            ("- Prohibited from granting loans against the security of the bank's own shares.", 9, False, 433),
            ("- Prohibited from advancing credit facilities to Bank Directors, senior executives, or their relatives", 9, False, 420),
            ("  without explicit prior approval by the Board of Directors / Management Credit Committee.", 9, False, 407),
            ("1.6 Early Warning Red-Flag Triggers (Mandatory Escalation within 48 Hours):", 10, True, 387),
            ("- Unhedged foreign currency exposure exceeding 25% of borrower tangible net worth.", 9, False, 372),
            ("- Frequent resignation of statutory auditors or change in accounting policies in the last 24 months.", 9, False, 359),
            ("- Routing of funds through non-consortium accounts or unverified sister concern transactions.", 9, False, 346),
        ],
        # PAGE 2
        [
            ("SECTION 2: MANDATORY FINANCIAL BENCHMARK RATIOS & UNDERWRITING", 12, True, 740),
            ("2.1 Debt Service Coverage Ratio (DSCR):", 10, True, 715),
            ("- Minimum average DSCR over the term loan repayment tenure must not be less than 1.50x.", 9, False, 700),
            ("- In any individual operational year, projected DSCR under sensitivity stress tests must not fall below 1.25x.", 9, False, 687),
            ("2.2 Current Ratio & Working Capital Liquidity:", 10, True, 667),
            ("- Minimum Current Ratio (Current Assets / Current Liabilities) is established at 1.33x for operating limits.", 9, False, 652),
            ("- Borrowers with current ratio between 1.20x and 1.33x require mandatory Credit Risk Mitigation approvals.", 9, False, 639),
            ("2.3 Total Outside Liabilities to Tangible Net Worth (TOL / TNW Leverage):", 10, True, 619),
            ("- Manufacturing Sector: Maximum allowable TOL/TNW is capped at 3.50x.", 9, False, 604),
            ("- Trading & Services Sector: Maximum allowable TOL/TNW is capped at 4.00x.", 9, False, 591),
            ("- Infrastructure Projects: Maximum allowable TOL/TNW is capped at 5.00x during implementation phase.", 9, False, 578),
            ("2.4 Interest Coverage Ratio (ICR):", 10, True, 558),
            ("- Operating EBITDA divided by Gross Interest Expense must maintain a minimum benchmark of 2.00x.", 9, False, 543),
            ("2.5 Promoters Equity Contribution & Margin Norms:", 10, True, 523),
            ("- Minimum Promoters' unencumbered equity contribution is 25% of total estimated project cost.", 9, False, 508),
            ("- Upfront equity infusion verification by statutory auditor certificate required prior to first loan drawdown.", 9, False, 495),
            ("2.6 Working Capital Assessment Methodologies:", 10, True, 475),
            ("- Nayak Committee Turnover Method: Applicable for limits up to INR 5 Crores (20% of projected gross turnover).", 9, False, 460),
            ("- Cash Budget Method: Mandatory for infrastructure contractors, seasonal agro-processing, and software services.", 9, False, 447),
            ("- Tandon Committee MPBF (Method II): Mandatory for large manufacturing credits exceeding INR 10 Crores.", 9, False, 434),
        ],
        # PAGE 3
        [
            ("SECTION 3: LOAN-TO-VALUE (LTV) LIMITS & COLLATERAL SECURITY NORMS", 12, True, 740),
            ("3.1 Commercial Real Estate (CRE) LTV & Valuation:", 10, True, 715),
            ("- Maximum LTV for Commercial Real Estate loans (commercial complexes, IT parks) is strictly capped at 75%.", 9, False, 700),
            ("- Valuation reports from two independent registered valuers required for exposures above INR 10 Crores.", 9, False, 687),
            ("3.2 Individual Housing Loan LTV Framework & Risk Weights:", 10, True, 667),
            ("- Tier 1 (Loans up to INR 30 Lakhs): Maximum LTV = 90% (Standard Risk Weight: 35%).", 9, False, 652),
            ("- Tier 2 (Loans above INR 30 Lakhs to 75 Lakhs): Maximum LTV = 80% (Standard Risk Weight: 50%).", 9, False, 639),
            ("- Tier 3 (Loans above INR 75 Lakhs): Maximum LTV = 75% (Standard Risk Weight: 75%).", 9, False, 626),
            ("3.3 Mandatory CERSAI Registration:", 10, True, 606),
            ("- All equitable mortgages, registered mortgages, and hypothecations must be registered with CERSAI", 9, False, 591),
            ("  (Central Registry of Securitisation Asset Reconstruction and Security Interest) within 30 days.", 9, False, 578),
            ("- Non-compliance within 30 days results in mandatory internal audit reporting as Severe Documentation Defect.", 9, False, 565),
            ("3.4 Title Search Reports (TSR) & Legal Due Diligence:", 10, True, 545),
            ("- Title search report verifying non-encumbrance and continuous 30-year chain of title by panel advocate.", 9, False, 530),
            ("3.5 Insurance Coverage & Stock Audits:", 10, True, 510),
            ("- 100% comprehensive insurance coverage for fire, earthquake, and transit with Bank Hypothecation Clause.", 9, False, 495),
            ("- Annual stock and book debt audit by independent empanelled CA firm mandatory for limits >= INR 5 Crores.", 9, False, 482),
        ],
        # PAGE 4
        [
            ("SECTION 4: PRUDENTIAL ASSET CLASSIFICATION & PROVISIONING NORMS (IRAC)", 12, True, 740),
            ("4.1 Special Mention Account (SMA) Early Warning Sub-Categories:", 10, True, 715),
            ("- SMA-0: Principal or interest payment overdue between 1 to 30 days.", 9, False, 700),
            ("- SMA-1: Principal or interest payment overdue between 31 to 60 days (Mandatory Joint Lenders Forum).", 9, False, 687),
            ("- SMA-2: Principal or interest payment overdue between 61 to 90 days (Mandatory CRILC reporting).", 9, False, 674),
            ("4.2 Non-Performing Asset (NPA) Classification Criteria:", 10, True, 654),
            ("- Term Loans: Interest or principal instalment remains overdue for more than 90 days.", 9, False, 639),
            ("- Cash Credit / Overdraft: Account remains 'Out of Order' (outstanding continuously exceeds limit) for > 90 days.", 9, False, 626),
            ("- Agricultural Loans: Unpaid for 2 crop seasons (short duration crops) or 1 crop season (long duration crops).", 9, False, 613),
            ("4.3 Prudential Provisioning Rates on Loan Assets:", 10, True, 593),
            ("- Standard Assets (General Commercial): 0.40% provisioning on total funded outstanding.", 9, False, 578),
            ("- Standard Assets (Commercial Real Estate - CRE): 1.00% provisioning on funded outstanding.", 9, False, 565),
            ("- Standard Assets (Direct Agriculture & SME Units): 0.25% provisioning.", 9, False, 552),
            ("- Substandard Assets (NPA <= 12 months): 15% provision on secured portion; 25% on unsecured portion.", 9, False, 539),
            ("- Doubtful-1 (D1, NPA 1-2 years): 25% secured provision + 100% unsecured provision.", 9, False, 526),
            ("- Doubtful-2 (D2, NPA 2-3 years): 40% secured provision + 100% unsecured provision.", 9, False, 513),
            ("- Doubtful-3 (D3, NPA > 3 years): 100% provision on total outstanding exposure.", 9, False, 500),
            ("- Loss Assets: 100% complete write-off or provision immediately upon identification.", 9, False, 487),
        ],
        # PAGE 5
        [
            ("SECTION 5: LARGE EXPOSURE FRAMEWORK (LEF) & CONCENTRATION LIMITS", 12, True, 740),
            ("5.1 Single Counterparty Exposure Ceiling:", 10, True, 715),
            ("- Total exposure to a single counterparty / corporate entity cannot exceed 20% of Bank's Eligible Tier 1 Capital.", 9, False, 700),
            ("- In exceptional circumstances, the Board of Directors may approve an additional 5% exposure (up to 25% max).", 9, False, 687),
            ("5.2 Connected Group Counterparties Limit:", 10, True, 667),
            ("- Total exposure to a group of connected counterparties is strictly capped at 25% of Eligible Tier 1 Capital.", 9, False, 652),
            ("5.3 Sectoral & Capital Market Exposure (CME) Ceilings:", 10, True, 632),
            ("- Capital Market Exposure (equity shares, convertible bonds, underwriting): Capped at 40% of Bank Net Worth.", 9, False, 617),
            ("- Real Estate Sectoral Cap: Aggregate commercial real estate lending capped at 15% of total bank loan book.", 9, False, 604),
            ("5.4 Unhedged Foreign Currency Exposure (UFCE) Surcharge:", 10, True, 584),
            ("- Borrowers with unhedged FX exposures face mandatory incremental capital risk weights (20% to 100%) and", 9, False, 569),
            ("  incremental provisioning between 10 to 40 basis points based on potential foreign currency earnings volatility.", 9, False, 556),
            ("5.5 Priority Sector Lending (PSL) Targets:", 10, True, 536),
            ("- Mandatory 40% of Adjusted Net Bank Credit (ANBC) allocated to Agriculture, Micro, Small & Medium Enterprises.", 9, False, 521),
        ],
        # PAGE 6
        [
            ("SECTION 6: ESG DUE DILIGENCE, DISBURSEMENT & AUDIT CHECKLIST", 12, True, 740),
            ("6.1 Environmental, Social & Governance (ESG) Due Diligence:", 10, True, 715),
            ("- Phase 1 Environmental Site Assessment (ESA) mandatory for industrial projects exceeding INR 25 Crores.", 9, False, 700),
            ("- Pollution Control Board Consents: Valid Consent to Establish (CTE) and Consent to Operate (CTO) mandatory.", 9, False, 687),
            ("6.2 End-Use of Funds Monitoring & Anti-Diversion Safeguards:", 10, True, 667),
            ("- Direct disbursement into verified supplier/contractor bank accounts; direct borrower cash drawings prohibited.", 9, False, 652),
            ("- Quarterly Chartered Accountant End-Use Certificate required for all working capital limits > INR 1 Crore.", 9, False, 639),
            ("6.3 Mandatory Pre-Disbursement Credit Committee Checklist:", 10, True, 619),
            ("[X] 1. Sanction Letter acceptance and financial covenants formally countersigned by authorized signatories.", 9, False, 604),
            ("[X] 2. Personal & Corporate Guarantees executed with verified net-worth CA certificates.", 9, False, 591),
            ("[X] 3. Registrar of Companies (ROC) First Charge / Mortgage registered (Form CHG-1) within 30 days.", 9, False, 578),
            ("[X] 4. CERSAI Security Interest Unique ID generated and archived in loan management repository.", 9, False, 565),
            ("[X] 5. Comprehensive Insurance Policy with Bank Mortgage & Hypothecation Clause in place.", 9, False, 552),
            ("[X] 6. Clean Title Search Report (TSR) from empanelled advocate with 30-year non-encumbrance verification.", 9, False, 539),
            ("6.4 Periodic Post-Disbursement Review Schedule:", 10, True, 519),
            ("- Quarterly review of financial performance statements and stock statements.", 9, False, 504),
            ("- Annual comprehensive credit rating review and collateral re-inspection.", 9, False, 491),
        ]
    ]

    # Build PDF binary objects
    pdf_objects = []
    
    # 1: Catalog
    pdf_objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    # 2: Pages
    num_pages = len(pages)
    kids = " ".join([f"{3 + i*3} 0 R" for i in range(num_pages)])
    pdf_objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>\nendobj\n")
    
    # Fonts
    pdf_objects.append("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")
    pdf_objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    stream_objs = []
    for i, page_lines in enumerate(pages):
        page_obj_id = 3 + i*3
        stream_obj_id = 20 + i
        
        # Build stream content
        stream_content = ["BT"]
        prev_y = 740
        for text, size, is_bold, y in page_lines:
            font = "/F1" if is_bold else "/F2"
            # escape parentheses and backslashes in PDF text
            safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_content.append(f"{font} {size} Tf")
            stream_content.append(f"50 {y} Td")
            stream_content.append(f"({safe_text}) Tj")
            stream_content.append(f"-50 -{y} Td")
        stream_content.append("ET\n")
        stream_str = "\n".join(stream_content)
        stream_bytes = stream_str.encode("latin-1")
        
        # Page object
        page_str = (
            f"{page_obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
            f"/Contents {stream_obj_id} 0 R >>\nendobj\n"
        )
        pdf_objects.append(page_str)
        
        # Stream object
        stream_obj_str = (
            f"{stream_obj_id} 0 obj\n"
            f"<< /Length {len(stream_bytes)} >>\n"
            f"stream\n{stream_str}\nendstream\nendobj\n"
        )
        stream_objs.append((stream_obj_id, stream_obj_str))

    for _, sobj in stream_objs:
        pdf_objects.append(sobj)

    # Let's write with correct xref
    # We can calculate byte offsets
    header = "%PDF-1.4\n"
    body_parts = []
    offsets = {}
    
    cur_offset = len(header.encode("latin-1"))
    
    # Sort objects by id
    all_raw_objs = []
    # parse object IDs from pdf_objects
    for obj in pdf_objects:
        obj_id = int(obj.split()[0])
        all_raw_objs.append((obj_id, obj))
        
    all_raw_objs.sort(key=lambda x: x[0])
    
    for obj_id, obj_text in all_raw_objs:
        offsets[obj_id] = cur_offset
        obj_bytes = obj_text.encode("latin-1")
        cur_offset += len(obj_bytes)
        body_parts.append(obj_bytes)

    max_id = max(offsets.keys())
    xref_lines = [f"xref\n0 {max_id + 1}\n0000000000 65535 f \n"]
    for i in range(1, max_id + 1):
        if i in offsets:
            xref_lines.append(f"{offsets[i]:010d} 00000 n \n")
        else:
            xref_lines.append("0000000000 65535 f \n")
            
    xref_str = "".join(xref_lines)
    trailer_str = (
        f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\n"
        f"startxref\n{cur_offset}\n%%EOF\n"
    )
    
    full_pdf = header.encode("latin-1") + b"".join(body_parts) + xref_str.encode("latin-1") + trailer_str.encode("latin-1")
    
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(full_pdf)
    print(f"Created PDF at: {filepath} ({len(full_pdf)} bytes)")


if __name__ == "__main__":
    out_pdf = Path("d:/loan-application-rag/RBIC_Loan_Compliance_Checking_Policy.pdf")
    build_pdf(out_pdf)
    reader = pypdf.PdfReader(str(out_pdf))
    print(f"Verified with pypdf: {len(reader.pages)} pages extracted.")
    for i, page in enumerate(reader.pages, start=1):
        txt = page.extract_text()
        print(f"--- PAGE {i} ({len(txt)} chars) ---")
        print(txt[:120].replace("\n", " ") + "...")
