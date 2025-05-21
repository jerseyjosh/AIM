import os
from email import policy
from email.parser import BytesParser

# load the .eml as bytes and parse it
eml_path = os.path.join(os.path.dirname(__file__), 'base_email.eml')
with open(eml_path, 'rb') as f:
    msg = BytesParser(policy=policy.default).parse(f)

# find the HTML part and get its decoded text
html_part = msg.get_body(preferencelist=('html',))
if not html_part:
    raise ValueError("No text/html part found in the email.")

html_content = html_part.get_content()  # already decoded to a str

# write it out
out_path = os.path.join(os.path.dirname(__file__), 'base_email.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
