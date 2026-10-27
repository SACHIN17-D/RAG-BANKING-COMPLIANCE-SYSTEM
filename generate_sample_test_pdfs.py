"""
Generates realistic sample banking policy PDF files for user testing.
"""
from pathlib import Path
import pypdf

def build_pdf_from_pages(pages_data, output_path: Path):
    pdf_objects = []
    pdf_objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    num_pages = len(pages_data)
    kids = " ".join([f"{3 + i*3} 0 R" for i in range(num_pages)])
    pdf_objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>\nendobj\n")
    
    pdf_objects.append("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")
    pdf_objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    stream_objs = []
    for i, page_lines in enumerate(pages_data):
        page_obj_id = 3 + i*3
        stream_obj_id = 20 + i
        
        stream_content = ["BT"]
        for text, size, is_bold, y in page_lines:
            font = "/F1" if is_bold else "/F2"
            safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_content.append(f"{font} {size} Tf")
            stream_content.append(f"50 {y} Td")
            stream_content.append(f"({safe_text}) Tj")
            stream_content.append(f"-50 -{y} Td")
        stream_content.append("ET\n")
        stream_str = "\n".join(stream_content)
        stream_bytes = stream_str.encode("latin-1")
        
        page_str = (
            f"{page_obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> "
            f"/Contents {stream_obj_id} 0 R >>\nendobj\n"
        )
        pdf_objects.append(page_str)
        
        stream_obj_str = (
            f"{stream_obj_id} 0 obj\n"
            f"<< /Length {len(stream_bytes)} >>\n"
            f"stream\n{stream_str}\nendstream\nendobj\n"
        )
        stream_objs.append((stream_obj_id, stream_obj_str))

    for _, sobj in stream_objs:
        pdf_objects.append(sobj)

    header = "%PDF-1.4\n"
    body_parts = []
    offsets = {}
    cur_offset = len(header.encode("latin-1"))
    
    all_raw_objs = []
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(full_pdf)


def generate_sba_pdf(dest: Path):
    pages = [
        # Page 1
        [
            ("SMALL BUSINESS ADMINISTRATION (SBA 7A & 504) UNDERWRITING POLICY", 15, True, 740),
            ("CREDIT RISK STANDARDS, GUARANTY FEES & ELIGIBILITY GUIDELINES", 11, True, 715),
            ("Document Ref: SBA-SOP-50-10-7 | Commercial Small Business Lending Unit", 9, False, 695),
            ("____________________________________________________________________________________________", 9, False, 685),
            ("SECTION 1: SBA 7(A) LOAN PROGRAM ELIGIBILITY & MAXIMUM LIMITS", 12, True, 660),
            ("1.1 Maximum Loan Size:", 10, True, 640),
            ("The statutory maximum loan amount for an SBA 7(a) standard loan facility is $5,000,000 USD.", 9, False, 625),
            ("For SBA Express loans, the maximum limit is strictly capped at $500,000 USD.", 9, False, 612),
            ("1.2 SBA Guaranty Percentage Schedule:", 10, True, 592),
            ("- Loans up to $150,000: SBA provides a maximum 85% government guaranty to the lending bank.", 9, False, 577),
            ("- Loans above $150,000 up to $5,000,000: SBA provides a maximum 75% guaranty.", 9, False, 564),
            ("- SBA Express Loans: SBA provides a 50% fixed government guaranty.", 9, False, 551),
            ("1.3 Minimum Credit Score & Personal Guarantee Requirements:", 10, True, 531),
            ("- Minimum Small Business Scoring Service (SBSS) score of 155 for loans under $500,000.", 9, False, 516),
            ("- Minimum Personal FICO score of 680 for all principal owners and key guarantors.", 9, False, 503),
            ("- Unconditional personal guarantees mandatory for every individual holding 20% or more equity ownership.", 9, False, 490),
        ],
        # Page 2
        [
            ("SECTION 2: CASH FLOW UNDERWRITING & EQUITY INJECTION REQUIREMENTS", 12, True, 740),
            ("2.1 Debt Service Coverage Ratio (DSCR) Benchmark:", 10, True, 715),
            ("- Minimum historical and projected global DSCR of 1.15x is required for all small business term loans.", 9, False, 700),
            ("- Global cash flow analysis must combine both business operating cash flow and personal owner cash flow.", 9, False, 687),
            ("2.2 Minimum Equity Injection Requirements:", 10, True, 667),
            ("- Start-up businesses (operating under 2 years): Minimum 10% cash equity injection of total project costs.", 9, False, 652),
            ("- Complete Business Acquisition (Change of Ownership): Minimum 10% equity injection mandatory.", 9, False, 639),
            ("2.3 Allowable Loan Maturities:", 10, True, 619),
            ("- Working Capital Lines and Inventory Loans: Maximum maturity of 10 years.", 9, False, 604),
            ("- Equipment and Machinery Financing: Up to 10 years (or useful economic life of the asset).", 9, False, 591),
            ("- Owner-Occupied Real Estate (at least 51% occupied by borrower): Maximum maturity of 25 years.", 9, False, 578),
            ("2.4 Prohibited Business Types & Ineligible Entities:", 10, True, 558),
            ("- Real estate speculation, gambling establishments, payday lenders, and pyramid distribution entities.", 9, False, 543),
        ]
    ]
    build_pdf_from_pages(pages, dest)


def generate_cre_pdf(dest: Path):
    pages = [
        # Page 1
        [
            ("COMMERCIAL REAL ESTATE (CRE) MORTGAGE & CONSTRUCTION RISK MANUAL", 15, True, 740),
            ("LOAN-TO-VALUE CEILINGS, DEBT YIELDS & STRESS TESTING REQUIREMENTS", 11, True, 715),
            ("Document Ref: CRE-PRUD-2026-M4 | Institutional Real Estate Underwriting", 9, False, 695),
            ("____________________________________________________________________________________________", 9, False, 685),
            ("SECTION 1: MAXIMUM LOAN-TO-VALUE (LTV) CEILINGS BY PROPERTY TYPE", 12, True, 660),
            ("1.1 Raw Land & Land Acquisition Loans:", 10, True, 640),
            ("Maximum allowable LTV is strictly capped at 65% of the lower of cost or appraised as-is value.", 9, False, 625),
            ("1.2 Land Development & Infrastructure:", 10, True, 605),
            ("Maximum allowable LTV is capped at 75% of total verified infrastructure development cost.", 9, False, 590),
            ("1.3 Commercial Construction (Office, Industrial, Retail, Hotel):", 10, True, 570),
            ("Maximum allowable Loan-to-Cost (LTC) is capped at 80% with minimum 20% hard cash equity in place.", 9, False, 555),
            ("1.4 Stabilized Multifamily Residential Properties (5+ Units):", 10, True, 535),
            ("Maximum allowable LTV is 80% for stabilized multifamily properties with sustained 90%+ occupancy.", 9, False, 520),
            ("1.5 Stabilized Commercial Office & Retail Centers:", 10, True, 500),
            ("Maximum allowable LTV is 75% with minimum 85% physical and economic pre-leasing verified.", 9, False, 485),
        ],
        # Page 2
        [
            ("SECTION 2: DEBT YIELD, SENSITIVITY TESTING & ENVIRONMENTAL AUDITS", 12, True, 740),
            ("2.1 Minimum Debt Yield Benchmark:", 10, True, 715),
            ("- Net Operating Income (NOI) divided by total loan amount must equal or exceed 9.50% at stabilization.", 9, False, 700),
            ("- For hospitality and lodging assets, minimum required Debt Yield is 11.00%.", 9, False, 687),
            ("2.2 Interest Rate Sensitivity & Refinance Stress Test:", 10, True, 667),
            ("- Underwriters must model a mandatory +300 bps (3.00%) upward interest rate stress scenario.", 9, False, 652),
            ("- Stressed DSCR under the +300 bps rate shock must not drop below 1.10x.", 9, False, 639),
            ("2.3 Interest & Operating Expense Reserves:", 10, True, 619),
            ("- Mandatory upfront escrow of 6 months of principal, interest, taxes, and insurance (PITI) debt reserve.", 9, False, 604),
            ("2.4 Environmental Site Assessment (ESA) Norms:", 10, True, 584),
            ("- Phase I Environmental Site Assessment (ESA) by certified environmental engineer mandatory for all loans > $1M.", 9, False, 569),
            ("- Any identified recognized environmental condition (REC) automatically mandates a Phase II subsurface test.", 9, False, 556),
        ]
    ]
    build_pdf_from_pages(pages, dest)


if __name__ == "__main__":
    from pathlib import Path
    import shutil

    base_dir = Path("d:/loan-application-rag/sample_test_pdfs")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    sba_path = base_dir / "SBA_Small_Business_Loan_Underwriting_Policy.pdf"
    cre_path = base_dir / "CRE_Commercial_Mortgage_Risk_Manual.pdf"

    generate_sba_pdf(sba_path)
    generate_cre_pdf(cre_path)
    print(f"Generated {sba_path} and {cre_path}")

    # Copy to Downloads
    downloads_dir = Path("C:/Users/sachi/Downloads")
    if downloads_dir.exists():
        shutil.copy(sba_path, downloads_dir / sba_path.name)
        shutil.copy(cre_path, downloads_dir / cre_path.name)
        print("Copied sample test PDFs to Downloads folder.")
