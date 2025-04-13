import argparse
import re
import string
import os
import uuid
import vobject
import chardet
import zipfile

# Encoding conversion
def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw = f.read()
        result = chardet.detect(raw)
        return result["encoding"]

def convert_to_utf8(input_file, temp_file):
    encoding = detect_encoding(input_file)
    with open(input_file, "r", encoding=encoding, errors="replace") as f:
        content = f.read()
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(content)

# Strip non-printable characters
def remove_non_printable(input_file, output_file):
    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        content = ''.join(c if c in string.printable else '?' for c in f.read())
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

# Fallback cleaning
def clean_name(name):
    name = re.sub(r'[*/\\<>|:\"!?#]', '', name)
    name = re.sub(r'\b\d{1,2}[/\\\-.]?\d{1,2}[/\\\-.]?\d{2,4}\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    if not name:
        return "Unknown"
    if name.isalpha() and len(name) > 1:
        return name.capitalize()
    return name

def fix_phone(phone):
    phone = re.sub(r'(;|w)ext=\d+', '', phone)
    phone = re.sub(r'\s+X\d+', '', phone)
    if phone.startswith('*') or phone.startswith('#') or '#' in phone or '*' in phone:
        return ""
    if any(word in phone.lower() for word in ['rs', 'pensou', 'ensou', 'posso', 'dizer', 'segredo', 'estado']):
        return ""
    phone = re.sub(r'[^\d\+\(\)\s\-\.]', '', phone)
    if len(re.sub(r'[^\d]', '', phone)) < 5:
        return ""
    return phone.strip()

# Clean VCARD
def fast_cleanup_with_fallbacks(input_file, cleaned_file, autoclean_log_file):
    cleaned_cards = []
    log_entries = []

    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    vcards = re.split(r'(BEGIN:VCARD.*?END:VCARD)', content, flags=re.DOTALL)

    for vcard in vcards:
        if 'BEGIN:VCARD' not in vcard or 'END:VCARD' not in vcard:
            continue

        lines = vcard.strip().splitlines()
        fixed_lines = []
        fn_found = False
        uid_found = False
        has_version = False

        for line in lines:
            if line.startswith('FN:'):
                raw_name = line[3:].strip()
                name = clean_name(raw_name)
                fixed_lines.append(f'FN:{name}')
                if name != raw_name:
                    log_entries.append(f"[AUTO-CLEAN] FN fixed: '{raw_name}' -> '{name}'")
                fn_found = True
            elif line.startswith('N:'):
                raw = line[2:].strip()
                parts = raw.split(';') if raw else ['']
                fixed_lines.append('N:' + ';'.join(clean_name(p) for p in parts))
            elif line.startswith('TEL'):
                label, value = line.split(':', 1)
                value_clean = fix_phone(value.strip())
                if value_clean:
                    if value_clean != value.strip():
                        log_entries.append(f"[AUTO-CLEAN] TEL fixed: '{value.strip()}' -> '{value_clean}'")
                    fixed_lines.append(f'{label}:{value_clean}')
            elif line.startswith('VERSION:'):
                has_version = True
                fixed_lines.append('VERSION:3.0')
            elif line.startswith('UID:'):
                uid_found = True
                fixed_lines.append(line)
            elif line.startswith('BEGIN:VCARD'):
                fixed_lines.append('BEGIN:VCARD')
            else:
                fixed_lines.append(line)

        if not has_version:
            fixed_lines.insert(1, 'VERSION:3.0')
        if not uid_found:
            uid = str(uuid.uuid4())
            fixed_lines.insert(2, f'UID:{uid}')
            log_entries.append(f"[AUTO-GEN] UID added: {uid}")
        if not fn_found:
            fixed_lines.insert(3, 'FN:Unknown')
            log_entries.append("[AUTO-FILL] FN was missing, set to 'Unknown'")

        cleaned_cards.append('\n'.join(fixed_lines))

    with open(cleaned_file, "w", encoding="utf-8", newline="\n") as f:
        for card in cleaned_cards:
            f.write(card.strip() + "\n\n")

    with open(autoclean_log_file, "a", encoding="utf-8") as log:
        for entry in log_entries:
            log.write(entry + "\n")

# Validation class
def validate_contacts(vcf_file, valid_out, invalid_out, validation_log):
    valid = []
    invalid = []

    with open(vcf_file, "r", encoding="utf-8") as f:
        buffer = []
        for line in f:
            line = line.strip()
            if line == "BEGIN:VCARD":
                buffer = [line]
            elif line == "END:VCARD":
                buffer.append(line)
                try:
                    contact = vobject.readOne("\n".join(buffer))
                    errors = []
                    if not hasattr(contact, 'fn') or not contact.fn.value.strip():
                        errors.append("Missing full name (FN)")
                    if not (hasattr(contact, 'tel_list') and contact.tel_list or hasattr(contact, 'email_list') and contact.email_list):
                        errors.append("Missing phone and/or email")
                    if errors:
                        invalid.append("\n".join(buffer))
                        with open(validation_log, "a", encoding="utf-8") as log:
                            name = contact.fn.value if hasattr(contact, 'fn') else 'Unknown'
                            log.write(f"{name}:\n")
                            for e in errors:
                                log.write(f"  - {e}\n")
                            log.write("\n")
                    else:
                        valid.append("\n".join(buffer))
                except Exception as e:
                    invalid.append("\n".join(buffer))
                buffer = []
            elif buffer:
                buffer.append(line)

    with open(valid_out, "w", encoding="utf-8") as f:
        for c in valid:
            f.write(c + "\n\n")

    with open(invalid_out, "w", encoding="utf-8") as f:
        for c in invalid:
            f.write(c + "\n\n")

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean, validate and prepare VCF files for iOS compatibility")
    parser.add_argument("input_vcf", help="Path to input .vcf file")
    parser.add_argument("--output", default="valid.vcf", help="Output VCF file")
    parser.add_argument("--invalid", default="invalid.vcf", help="Invalid contacts VCF file")
    parser.add_argument("--log", default="autoclean_log.txt", help="Log file for autoclean operations")
    parser.add_argument("--validation", default="validation_log.txt", help="Validation report log file")
    args = parser.parse_args()

    temp_utf8 = "temp_utf8.vcf"
    temp_clean = "temp_clean.vcf"
    temp_cleaned = "temp_cleaned.vcf"

    convert_to_utf8(args.input_vcf, temp_utf8)
    remove_non_printable(temp_utf8, temp_clean)
    fast_cleanup_with_fallbacks(temp_clean, temp_cleaned, args.log)
    validate_contacts(temp_cleaned, args.output, args.invalid, args.validation)

    zip_path = args.output + ".zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(args.output, arcname=os.path.basename(args.output))

    print(f"[✓] Cleaned VCF saved to: {args.output}")
    print(f"[✓] Invalid VCF saved to: {args.invalid}")
    print(f"[✓] ZIP archive created at: {zip_path}")
    print(f"[ℹ] Autoclean log written to: {args.log}")
    print(f"[ℹ] Validation issues logged in: {args.validation}")
