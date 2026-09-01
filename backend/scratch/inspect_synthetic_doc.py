import os
import hashlib
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.modules.fixtures.registry import TestFixtureRegistry
from app.core.config import settings

def main():
    img_path = os.path.join(settings.UPLOAD_DIR, "DOC-3F44A169_ChatGPT Image Aug 31, 2026, 03_40_59 PM.png")
    print("Checking synthetic doc image path:", img_path)
    print("File exists:", os.path.exists(img_path))
    
    if os.path.exists(img_path):
        sha256_hash = TestFixtureRegistry.compute_sha256(img_path)
        print("SHA-256 Hash of image:", sha256_hash)
        print("Registered fixtures in TestFixtureRegistry:")
        for k, v in TestFixtureRegistry.__dict__.items():
            if k == "REGISTERED_FIXTURES":
                print(v)
        
        # Test pipeline processing under strict mode
        settings.DOCUMENT_VALIDATION_MODE = "production"
        pipeline = DocumentIntelligencePipeline()
        res_strict = pipeline.process_document(img_path)
        print("\n--- STRICT MODE RESULT ---")
        print("Document category:", res_strict.document_type)
        print("Validation overall status:", res_strict.validation.overall_status)
        print("Validation failure count:", res_strict.validation.failure_count)
        print("Validation inconsistency count:", res_strict.validation.inconsistency_count)
        for eval_item in res_strict.validation.evaluations:
            print(f"  Rule: {eval_item.rule_id} ({eval_item.rule_name}) -> Status: {eval_item.status}, Reason: {eval_item.reason}")
        if res_strict.mrz:
            print("MRZ present:", res_strict.mrz.is_present)
            print("MRZ format:", res_strict.mrz.mrz_format)
            print("MRZ valid checksums:", res_strict.mrz.all_check_digits_valid)
            for cd in res_strict.mrz.check_digits:
                print(f"    CheckDigit: {cd.field_name} (val: {cd.value}, exp: {cd.expected_digit}, valid: {cd.is_valid})")

if __name__ == "__main__":
    main()
