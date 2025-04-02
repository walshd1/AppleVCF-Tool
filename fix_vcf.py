#!/usr/bin/env python3
import re
import os
import sys

def clean_name(name):
    """Remove invalid characters from names"""
    # Remove symbols, special characters but keep basic punctuation
    cleaned = re.sub(r'[*/\\<>|:"!?#]', '', name)
    # Remove date-like patterns (e.g., 20/07/1954)
    cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', cleaned)
    # Replace multiple spaces with a single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def fix_phone_number(phone):
    """Fix invalid phone formats"""
    # Remove extension formats
    phone = re.sub(r'(;|w)ext=\d+', '', phone)
    phone = re.sub(r'\s+X\d+', '', phone)
    
    # Remove special characters
    if phone.startswith('*') or phone.startswith('#') or '#' in phone or '*' in phone:
        return ""  # Invalid special service numbers
    
    # Remove any non-standard text in phone numbers
    if any(word in phone.lower() for word in ['rs', 'pensou', 'ensou', 'posso', 'dizer', 'segredo', 'estado']):
        return ""
    
    # Fix common formatting issues
    phone = re.sub(r'[^\d\+\(\)\s\-\.]', '', phone)
    
    # Handle empty or too short results
    if len(re.sub(r'[^\d]', '', phone)) < 5:
        return ""
        
    return phone.strip()

def fix_vcf_file(input_path, output_path):
    """Fix issues in a VCF file based on common problems"""
    with open(input_path, 'r', encoding='utf-8', errors='replace') as infile:
        content = infile.read()
    
    # Split into individual vCards
    vcards = re.split(r'(BEGIN:VCARD.*?END:VCARD)', content, flags=re.DOTALL)
    
    fixed_content = []
    skipped_cards = 0
    
    for vcard in vcards:
        if not vcard.strip():
            continue
            
        if not 'BEGIN:VCARD' in vcard or not 'END:VCARD' in vcard:
            fixed_content.append(vcard)
            continue
        
        lines = vcard.split('\n')
        fixed_lines = []
        fn_value = ""
        has_phone_or_email = False
        
        for line in lines:
            # Fix full name
            if line.startswith('FN:'):
                fn_value = line[3:].strip()
                if not fn_value:
                    continue  # Skip empty names
                fixed_name = clean_name(fn_value)
                if fixed_name:
                    fixed_lines.append(f"FN:{fixed_name}")
            
            # Fix names structure
            elif line.startswith('N:'):
                parts = line[2:].split(';')
                for i in range(len(parts)):
                    parts[i] = clean_name(parts[i])
                fixed_lines.append(f"N:{';'.join(parts)}")
            
            # Fix phone numbers
            elif line.startswith('TEL;'):
                parts = line.split(':')
                if len(parts) > 1:
                    phone_value = parts[1].strip()
                    fixed_phone = fix_phone_number(phone_value)
                    
                    if fixed_phone:  # Only keep valid phones
                        has_phone_or_email = True
                        fixed_lines.append(f"{parts[0]}:{fixed_phone}")
            
            # Track if there's an email
            elif line.startswith('EMAIL;'):
                has_phone_or_email = True
                fixed_lines.append(line)
                
            # Keep other lines
            else:
                fixed_lines.append(line)
        
        # Only include the vCard if it has a name and either a phone or email
        if fn_value and has_phone_or_email:
            fixed_content.append('\n'.join(fixed_lines))
        else:
            skipped_cards += 1
    
    # Write fixed content to output file
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(fixed_content))
    
    print(f"Fixed VCF file saved to {output_path}")
    print(f"Skipped {skipped_cards} invalid vCards")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fix_vcf.py input.vcf output.vcf")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    fix_vcf_file(input_file, output_file)
