import argparse
import vobject
import re
import chardet
import string
import os

def detect_encoding(file_path):
    """Detect the file encoding to handle invalid characters properly."""
    with open(file_path, "rb") as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        print(f"[DEBUG] Detected encoding for {file_path}: {result['encoding']}")
        return result["encoding"]

def convert_to_utf8(input_file, output_file):
    """Convert a file to UTF-8 encoding."""
    detected_encoding = detect_encoding(input_file)
    with open(input_file, "r", encoding=detected_encoding, errors="replace") as f:
        content = f.read()
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[DEBUG] Converted {input_file} to UTF-8 -> {output_file}")

def remove_non_printable(input_file, output_file):
    """Remove non-printable characters from the file."""
    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        cleaned_content = ''.join(char if char in string.printable else '?' for char in f.read())
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(cleaned_content)
    print(f"[DEBUG] Removed non-printable characters -> {output_file}")

class VcfValidator:
    """Validator for identifying Apple-import issues in vCards."""
    INVALID_CHARS = re.compile(r'[<>|:*?"\\/]')

    def validate(self, contact):
        errors = []
        print(f"[DEBUG] Validating contact: {contact.fn.value if hasattr(contact, 'fn') else 'Unknown'}")

        # 1. Must have a full name
        if not hasattr(contact, 'fn') or not contact.fn.value:
            errors.append("Missing full name")

        # 2. Check for invalid characters
        if hasattr(contact, 'fn') and self.INVALID_CHARS.search(contact.fn.value):
            errors.append(f"Invalid characters in name: {contact.fn.value}")

        # 3. Must have at least a phone or email
        has_phone = hasattr(contact, 'tel') and contact.tel_list
        has_email = hasattr(contact, 'email') and contact.email_list
        if not (has_phone or has_email):
            errors.append("Missing phone and/or email")

        # 4. Validate phone formats if present
        if has_phone:
            for tel in contact.tel_list:
                if not re.match(r'^[+0-9\s\-\(\)]+$', tel.value):
                    errors.append(f"Invalid phone format: {tel.value}")

        print(f"[DEBUG] Validation errors for {contact.fn.value if hasattr(contact, 'fn') else 'Unknown'}: {errors}")
        return errors

def load_vcf(file_path):
    """Load contacts ensuring full VCARD entries are read and valid."""
    contacts = []
    current_vcard = []

    print(f"[DEBUG] Loading VCF file: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()

            if line.startswith("BEGIN:VCARD"):
                current_vcard = [line]

            elif line.startswith("END:VCARD"):
                current_vcard.append(line)
                vcard_text = "\n".join(current_vcard)
                
                try:
                    contact = vobject.readOne(vcard_text)
                    contacts.append(contact)
                except vobject.base.ParseError as e:
                    print(f"[DEBUG] Malformed contact: {vcard_text}\n[ERROR] {e}")

                current_vcard = []

            elif current_vcard:
                current_vcard.append(line)

    print(f"[DEBUG] Loaded {len(contacts)} valid contacts from {file_path}")
    return contacts

def save_vcf_with_errors(contacts, file_path):
    """Save invalid contacts to a VCF file and ensure all are logged."""
    if not contacts:
        print(f"[DEBUG] Warning: No contacts to save in {file_path}")
        return

    with open(file_path, "w", encoding="utf-8") as f_vcf:
        for contact, errors in contacts:
            try:
                vcf_data = contact.serialize()
                if vcf_data.strip():
                    f_vcf.write(vcf_data)
                    print(f"[DEBUG] Saved invalid contact: {contact.fn.value if hasattr(contact, 'fn') else 'Unknown'}")
                else:
                    print(f"[DEBUG] Skipping invalid contact with empty serialization: {contact}")
            except Exception as e:
                print(f"[ERROR] Failed to serialize contact: {contact} - {e}")

def extract_invalid_contacts(input_vcf, valid_vcf, invalid_vcf):
    """Extract invalid contacts and handle validation issues."""
    temp_utf8_file = "temp_utf8.vcf"
    temp_cleaned_file = "temp_cleaned.vcf"
    invalid_explanations_file = "invalid_explanations.txt"

    # 1. Convert to UTF-8
    convert_to_utf8(input_vcf, temp_utf8_file)
    
    # 2. Remove non-printable characters
    remove_non_printable(temp_utf8_file, temp_cleaned_file)

    # 3. Load contacts
    contacts = load_vcf(temp_cleaned_file)

    if not contacts:
        print(f"[DEBUG] No contacts loaded from {temp_cleaned_file}. Exiting.")
        return

    # 4. Validate contacts
    validator = VcfValidator()
    valid_contacts = []
    invalid_contacts = []

    with open(invalid_explanations_file, "w", encoding="utf-8") as explanation_file:
        for contact in contacts:
            errors = validator.validate(contact)
            if errors:
                invalid_contacts.append((contact, errors))
                explanation_file.write(
                    f"Contact: {contact.fn.value if hasattr(contact, 'fn') else 'Unknown'}\n"
                )
                for error in errors:
                    explanation_file.write(f"  - {error}\n")
                explanation_file.write("\n")
            else:
                valid_contacts.append((contact, []))

    print(f"[DEBUG] Valid contacts: {len(valid_contacts)}, Invalid contacts: {len(invalid_contacts)}")

    # 5. Save contacts
    save_vcf_with_errors(valid_contacts, valid_vcf)
    save_vcf_with_errors(invalid_contacts, invalid_vcf)

    # 6. Cleanup
    os.remove(temp_utf8_file)
    os.remove(temp_cleaned_file)

    print(f"[DEBUG] Processing complete. Valid: {valid_vcf}, Invalid: {invalid_vcf}")
    print(f"[DEBUG] Invalid contact reasons saved in: {invalid_explanations_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract invalid contacts from a VCF file.")
    parser.add_argument("input_vcf", help="Path to the input VCF file")
    parser.add_argument("valid_vcf", help="Path to save valid contacts")
    parser.add_argument("invalid_vcf", help="Path to save invalid contacts")

    args = parser.parse_args()
    extract_invalid_contacts(args.input_vcf, args.valid_vcf, args.invalid_vcf)
