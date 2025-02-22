AppleVCF-Tool

📌 Overview

This Python script validates and cleans .vcf (vCard) files to ensure compatibility with Apple's iPhone Contacts import requirements. It performs the following functions:

✅ Converts VCF files to UTF-8 encoding.

✅ Removes non-printable characters.

✅ Parses and validates vCards using Apple’s vCard requirements.

✅ Separates valid and invalid contacts into separate VCF files.

✅ Logs detailed explanations of why contacts were marked invalid.

✅ Fully compatible with iPhone and macOS Contacts.app.

🔧 Installation

1. Clone the Repository

git clone https://github.com/walshd1/AppleVCF-Tool.git
cd AppleVCF-Tool

2. Install Dependencies

Ensure you have Python 3.7+ installed, then install the required dependencies:

pip install vobject chardet

🚀 Usage

Run the script with the following command:

python vcf_validator.py input.vcf valid.vcf invalid.vcf

Arguments

input.vcf → The original VCF file to process.

valid.vcf → Output file for valid Apple-compatible contacts.

invalid.vcf → Output file for invalid contacts that need correction.

Example

python vcf_validator.py contacts.vcf valid_contacts.vcf invalid_contacts.vcf

📂 Output Files

File Name

Description

valid.vcf

Contains Apple-compatible contacts ready for import.

invalid.vcf

Contains contacts that failed validation.

invalid_explanations.txt

Explains why each contact was invalid.

🛠 Features & Validation Rules

✅ Apple-Compatible Fixes

✔ Converts encoding to UTF-8.✔ Removes non-printable characters.✔ Ensures every contact has a Full Name (**)**.\
✔ Validates **phone numbers (**) & emails (``).✔ Checks for invalid characters in names (<>|:*?\"\/).✔ Filters malformed contacts to invalid.vcf.

🛑 Why a Contact Might Be Invalid

A contact is marked as invalid if:

Missing full name (FN field is empty).

Contains illegal characters in the name (<>|:*?\"\/).

Missing phone & email (must have at least one).

Phone number format is incorrect (must be +0123456789 or ()- separated).

📥 Importing to iPhone

Method 1: Using iCloud

Open iCloud.com.

Go to Contacts.

Click the gear icon (⚙️) at the bottom-left.

Select Import vCard and choose valid.vcf.

Method 2: Direct Import

Send valid.vcf to your iPhone via email or AirDrop.

Open the file and select Add to Contacts.

🔎 Debugging

All processing steps are logged with [DEBUG] messages.

If valid.vcf is empty, check:

invalid_explanations.txt → Lists why contacts failed.

invalid.vcf → Should contain invalid contacts.

⚡ Contributions

Pull requests are welcome! If you find a bug or want to suggest improvements:

Fork the repository.

Create a new branch (fix-bug, add-feature).

Submit a pull request.

📜 License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

You are free to use, modify, and distribute this software under the terms of the GPL-3.0 license. See the LICENSE file for details.
