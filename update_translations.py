import polib
import os

po_path = r'd:\Jay\cws\09-07-26\SMS_09_07_2026\SMS09_07\locale\hi\LC_MESSAGES\django.po'
mo_path = r'd:\Jay\cws\09-07-26\SMS_09_07_2026\SMS09_07\locale\hi\LC_MESSAGES\django.mo'

po = polib.pofile(po_path)

missing = {
    "Generate Report": "रिपोर्ट जनरेट करें",
    "Batch No": "बैच नं.",
    "PO No": "पीओ नं.",
    "Product": "उत्पाद",
    "Stock": "स्टॉक",
    "Filter": "फ़िल्टर"
}

for msgid, msgstr in missing.items():
    entry = po.find(msgid)
    if entry:
        entry.msgstr = msgstr
    else:
        entry = polib.POEntry(
            msgid=msgid,
            msgstr=msgstr
        )
        po.append(entry)

po.save(po_path)
po.save_as_mofile(mo_path)
print("Updated PO and compiled to MO successfully with new strings.")
